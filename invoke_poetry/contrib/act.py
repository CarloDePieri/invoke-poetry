import hashlib
from pathlib import Path
from typing import List, NamedTuple, Optional

from invoke import Context  # type: ignore[attr-defined]

from invoke_poetry.logs import Colors, error, info, warn


class DockerCacheImage(NamedTuple):
    lock_md5: str
    image_id: str


class ActJobController:
    """An interface to interact with docker container and images related to act."""

    job_file: Path
    act_dev_prefix: str

    def __init__(
        self,
        job_file: Path,
        job_name: str,
    ) -> None:
        self.job_file = job_file
        self.act_dev_prefix = f"act-{job_file.stem}-{job_name}"

    def print_status(self, context: Context) -> None:
        """Print a report of all docker resources linked to this act job."""
        self._print_container_list(
            "Act Job containers:", self.list_job_container_ids(context)
        )

    @staticmethod
    def _print_container_list(heading: str, containers: List[str]) -> None:
        """Print the given container id list."""
        print(heading)
        if containers:
            for container_id in containers:
                print(f"\t{container_id}")
        else:
            print(f"\t{Colors.FAIL}none{Colors.ENDC}")

    def list_job_container_ids(self, c: Context) -> List[str]:
        """Return a list of ids of containers whose name starts with `self.act_dev_prefix`."""
        return self.list_container_ids(c, self.act_dev_prefix)

    def delete_job_containers(self, c: Context) -> List[str]:
        """Delete all container which name starts with `self.act_dev_prefix`. Return a list of all deleted
        container ids."""
        return self.delete_containers(c, self.list_job_container_ids(c))

    @staticmethod
    def list_container_ids(c: Context, filter_with: str) -> List[str]:
        """Filter containers using the given `search` string and return a list of corresponding ids."""
        ids = []
        result = c.run(f"docker ps -a | grep '{filter_with}'", hide=True, warn=True)
        if result:
            for line in (line for line in result.stdout.split("\n") if len(line) > 0):
                ids.append(line.split(" ")[0])
            return ids
        else:
            return ids

    def delete_containers(
        self, context: Context, container_list: List[str]
    ) -> List[str]:
        """Delete containers based on the given ids. Return a list of deleted container ids."""
        return self._delete(
            context=context, delete_command="docker rm -f", entry_ids=container_list
        )

    def delete_images(self, context: Context, image_ids: List[str]) -> List[str]:
        """Delete images based on the given ids. Return a list of deleted image ids."""
        return self._delete(
            context=context, delete_command="docker rmi", entry_ids=image_ids
        )

    @staticmethod
    def _delete(
        context: Context, delete_command: str, entry_ids: List[str]
    ) -> List[str]:
        """TODO"""
        deleted = []
        for entry_id in entry_ids:
            result = context.run(f"{delete_command} {entry_id}", pty=True, hide=True)
            if result and result.return_code == 0:
                deleted.append(result.stdout.rstrip("\r").rstrip("\n"))
        return deleted

    def open_shell_in_job_container(
        self, context: Context, env_file: Optional[str] = None
    ) -> None:
        job_containers = self.list_job_container_ids(context)
        if job_containers:
            self.open_shell(context, container_id=job_containers[0], env_file=env_file)
        else:
            error("No Job container found!")

    @staticmethod
    def open_shell(
        context: Context, container_id: str, env_file: Optional[str] = None
    ) -> None:
        """TODO"""
        env_str = ""
        if env_file:
            env_str = f"--env-file {env_file} "
        context.run(
            "docker exec " + env_str + f"-it {container_id} bash",
            pty=True,
        )


class ActCachedJobController(ActJobController):
    """TODO"""

    cache_file: Path
    act_cache_prefix: str
    docker_base_tag: str
    docker_cache_tag_prefix: str

    def __init__(
        self,
        job_file: Path,
        job_name: str,
        cache_file: Path,
        cache_job_name: str,
        docker_base_tag: str,
        docker_cache_tag_prefix: str,
    ) -> None:
        """TODO"""
        super().__init__(job_file=job_file, job_name=job_name)
        self.cache_file = cache_file
        self.act_cache_prefix = f"act-{cache_file.stem}-{cache_job_name}"
        self.docker_base_tag = docker_base_tag
        self.docker_cache_tag_prefix = (
            f"{docker_cache_tag_prefix}-{self.act_dev_prefix[4:]}"
        )

    def list_cache_container_ids(self, c: Context) -> List[str]:
        """Return a list of ids of containers whose name starts with `self.act_cache_prefix`."""
        return self.list_container_ids(c, self.act_cache_prefix)

    def delete_cache_containers(self, c: Context) -> List[str]:
        """Delete all container which name starts with `self.act_cache_prefix`. Return a list of all deleted
        container ids."""
        return self.delete_containers(c, self.list_cache_container_ids(c))

    def delete_cache_images(self, context: Context) -> List[str]:
        """Delete all images which name starts with `self.docker_cache_tag_prefix`. Return a list of all deleted
        image ids."""
        return self.delete_images(
            context, [image.image_id for image in self.list_cache_images(context)]
        )

    def get_cache_image(
        self, build_command: str, context: Context, force_rebuild: bool = False
    ) -> str:
        """TODO"""
        # Recover existing cache images
        existing_cache_images = self.list_cache_images(context)

        if force_rebuild:
            info("Cache rebuild requesting, purging old one...")
            self.delete_job_containers(context)
            self.delete_cache_containers(context)
            self.delete_images(
                context, [image.image_id for image in existing_cache_images]
            )
            existing_cache_images = []

        lock_hash = self._get_cumulative_hash([Path("poetry.lock"), self.cache_file])

        if lock_hash not in (image.lock_md5 for image in existing_cache_images):
            if not force_rebuild:
                warn("Cache image not found!")
            # Create the new cache image
            cache_tag = self.new_cache(
                build_command=build_command,
                context=context,
                lock_hash=lock_hash,
            )
        else:
            # Make sure the up-to-date image does not get deleted
            existing_cache_images = [
                image for image in existing_cache_images if image.lock_md5 != lock_hash
            ]
            cache_tag = self._get_cache_tag(lock_hash)

        # delete old cache images
        self.delete_images(context, [image.image_id for image in existing_cache_images])
        info("Cache image ready!")
        return cache_tag

    def _get_cache_tag(self, lock_hash: str) -> str:
        """TODO"""
        return f"{self.docker_cache_tag_prefix}-{lock_hash}"

    def new_cache(self, build_command: str, context: Context, lock_hash: str) -> str:
        """TODO"""
        # Ensure no other container are present
        self.delete_job_containers(context)
        self.delete_cache_containers(context)
        # Build the cache container
        info("Building the cache container...")
        context.run(
            build_command,
            pty=True,
        )
        # Create an image out of it
        info("Saving the cache image...")
        cache_containers = self.list_cache_container_ids(context)
        cache_tag = self._get_cache_tag(lock_hash)
        if cache_containers:
            context.run(
                f"docker commit {cache_containers[0]} {cache_tag}",
                hide=False,
            )
        # Delete the cache container
        info("Cleaning up...")
        self.delete_cache_containers(context)
        return cache_tag

    def list_cache_images(self, context: Context) -> List[DockerCacheImage]:
        """TODO"""
        images = []
        result = context.run(
            f"docker images --all | grep '{self.docker_cache_tag_prefix}'",
            hide=True,
            warn=True,
        )
        if result:
            for line in (line for line in result.stdout.split("\n") if len(line) > 0):
                data = [el for el in line.split(" ") if len(el) > 0]
                md5_hash = data[0].replace(f"{self.docker_cache_tag_prefix}-", "")
                images.append(
                    DockerCacheImage(
                        lock_md5=md5_hash,
                        image_id=data[2],
                    )
                )
            return images
        else:
            return images

    @staticmethod
    def _get_cumulative_hash(files: List[Path]) -> str:
        """Return a md5 hashsum based on the given files."""
        hash_md5 = hashlib.md5()
        for lock_file in files:
            if not lock_file.is_file():
                error(f"Could not find `{lock_file}`!")
            with open(lock_file, "rb") as file_reader:
                for chunk in iter(lambda: file_reader.read(4096), b""):
                    # Read the file chunk by chunk and keep updating the hash
                    hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def print_status(self, context: Context) -> None:
        """Print a report of all the resources linked to this cached act job."""
        super().print_status(context)
        self._print_container_list(
            "Act Job Cache containers:", self.list_cache_container_ids(context)
        )
        images = self.list_cache_images(context)
        print("Act Job Cache images:")
        if images:
            for image in images:
                print(f"\t{image.image_id} (from lock hash {image.lock_md5})")
        else:
            print(f"\t{Colors.FAIL}none{Colors.ENDC}")

    def open_shell_in_cache_container(
        self, context: Context, env_file: Optional[str] = None
    ) -> None:
        """TODO"""
        cache_containers = self.list_cache_container_ids(context)
        if cache_containers:
            self.open_shell(
                context, container_id=cache_containers[0], env_file=env_file
            )
        else:
            error("No Cache container found!")
