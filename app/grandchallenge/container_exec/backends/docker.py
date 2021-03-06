# -*- coding: utf-8 -*-
import io
import json
import os
import tarfile
import uuid
from contextlib import contextmanager
from json import JSONDecodeError
from pathlib import Path
from typing import Tuple

import docker
from django.conf import settings
from django.core.files import File
from docker.api.container import ContainerApiMixin
from docker.errors import ContainerError

from grandchallenge.container_exec.exceptions import (
    InputError, ExecContainerError
)


class Executor(object):

    def __init__(
            self,
            *,
            job_id: uuid.UUID,
            input_files: Tuple[File, ...],
            exec_image: File,
            exec_image_sha256: str,
            results_file: Path,
    ):
        super().__init__()
        self._job_id = str(job_id)
        self._input_files = input_files
        self._exec_image = exec_image
        self._exec_image_sha256 = exec_image_sha256
        self._io_image = settings.CONTAINER_EXEC_IO_IMAGE
        self._results_file = results_file

        self._client = docker.DockerClient(
            base_url=settings.CONTAINER_EXEC_DOCKER_BASE_URL
        )

        self._input_volume = f'{self._job_id}-input'
        self._output_volume = f'{self._job_id}-output'

        self._run_kwargs = {
            'labels': {'job_id': self._job_id},
            'network_disabled': True,
            'mem_limit': settings.CONTAINER_EXEC_MEMORY_LIMIT,
            'cpu_period': settings.CONTAINER_EXEC_CPU_PERIOD,
            'cpu_quota': settings.CONTAINER_EXEC_CPU_QUOTA,
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        filter = {'label': f'job_id={self._job_id}'}

        for container in self._client.containers.list(filters=filter):
            container.stop()

        self._client.containers.prune(filters=filter)
        self._client.volumes.prune(filters=filter)

    def execute(self) -> dict:
        self._pull_images()
        self._create_io_volumes()
        self._provision_input_volume()
        self._execute_container()
        return self._get_result()

    def _pull_images(self):
        self._client.images.pull(repository=self._io_image)

        if self._exec_image_sha256 not in [
            img.id for img in self._client.images.list()
        ]:
            with self._exec_image.open('rb') as f:
                self._client.images.load(f)

    def _create_io_volumes(self):
        for volume in [self._input_volume, self._output_volume]:
            self._client.volumes.create(
                name=volume, labels=self._run_kwargs["labels"],
            )

    def _provision_input_volume(self):
        try:
            with cleanup(
                    self._client.containers.run(
                        image=self._io_image,
                        volumes={
                            self._input_volume: {
                                'bind': '/input/', 'mode': 'rw'
                            }
                        },
                        detach=True,
                        tty=True,
                        **self._run_kwargs,
                    )
            ) as writer:
                self._copy_input_files(writer=writer)
        except Exception as exc:
            raise InputError(str(exc))

    def _copy_input_files(self, writer):
        for file in self._input_files:
            put_file(
                container=writer,
                src=file,
                dest=f"/input/{Path(file.name).name}"
            )

    def _execute_container(self):
        try:
            self._client.containers.run(
                image=self._exec_image_sha256,
                volumes={
                    self._input_volume: {'bind': '/input/', 'mode': 'rw'},
                    self._output_volume: {'bind': '/output/', 'mode': 'rw'},
                },
                **self._run_kwargs,
            )
        except ContainerError as exc:
            raise ExecContainerError(exc.stderr.decode())

    def _get_result(self) -> dict:
        try:
            result = self._client.containers.run(
                image=self._io_image,
                volumes={
                    self._output_volume: {'bind': '/output/', 'mode': 'ro'}
                },
                command=f"cat {self._results_file}",
                **self._run_kwargs,
            )
        except ContainerError as exc:
            raise ExecContainerError(exc.stderr.decode())

        try:
            result = json.loads(
                result.decode(),
                parse_constant=lambda x: None, # Removes -inf, inf and NaN
            )
        except JSONDecodeError as exc:
            raise ExecContainerError(exc.msg)

        return result


@contextmanager
def cleanup(container: ContainerApiMixin):
    """
    Cleans up a docker container which is running in detached mode

    :param container: An instance of a container
    :return:
    """
    try:
        yield container

    finally:
        container.stop()
        container.remove(force=True)


def put_file(*, container: ContainerApiMixin, src: File, dest: str) -> ():
    """
    Puts a file on the host into a container.
    This method will create an in memory tar archive, add the src file to this
    and upload it to the docker container where it will be unarchived at dest.

    :param container: The container to write to
    :param src: The path to the source file on the host
    :param dest: The path to the target file in the container
    :return:
    """
    tar_b = io.BytesIO()

    tarinfo = tarfile.TarInfo(name=os.path.basename(dest))
    tarinfo.size = src.size

    with tarfile.open(fileobj=tar_b, mode='w') as tar, src.open('rb') as f:
        tar.addfile(tarinfo, fileobj=f)

    tar_b.seek(0)
    container.put_archive(os.path.dirname(dest), tar_b)
