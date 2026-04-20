from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable

log = logging.getLogger(__name__)

_TRUTHY_VALUES = {"1", "true", "yes", "on"}


class OfflineBuiltinDatasetMissingFiles(RuntimeError):
    """Raised when VDB_OFFLINE=true and required local dataset files are absent."""


def offline_enabled() -> bool:
    return os.getenv("VDB_OFFLINE", "").strip().lower() in _TRUTHY_VALUES


def dataset_identifier_from_dir_name(dataset_dir_name: str) -> str:
    try:
        from vectordb_bench.backend.dataset import DatasetWithSizeType

        for dataset_type in DatasetWithSizeType:
            manager = dataset_type.get_manager()
            if manager.data.dir_name.lower() == dataset_dir_name.lower():
                return dataset_type.name
    except Exception:
        log.debug("Failed to map dataset dir name to DatasetWithSizeType", exc_info=True)

    return dataset_dir_name


def expected_files_for_manager(manager, filters=None) -> list[str]:
    if filters is None:
        from vectordb_bench.backend.filter import non_filter

        filters = non_filter

    manager.train_files = manager.data.train_files

    files = list(manager.train_files)
    if manager.data.with_gt:
        files.extend([filters.groundtruth_file, manager.data.test_file])
    if manager.data.with_scalar_labels and manager.data.scalar_labels_file_separated:
        files.append(manager.data.scalar_labels_file)
    return [file for file in files if file is not None]


def verify_local_dataset_files(
    dataset_identifier: str,
    dataset_dir_name: str,
    files: Iterable[str],
    local_ds_root: Path,
    configured_dataset_dir: Path | str | None = None,
) -> None:
    local_ds_root = Path(local_ds_root)
    configured_dataset_dir = Path(configured_dataset_dir) if configured_dataset_dir else local_ds_root

    required_files = list(files)
    missing_files = [file for file in required_files if not local_ds_root.joinpath(file).is_file()]
    if missing_files:
        missing_list = ", ".join(missing_files)
        msg = (
            "VDB_OFFLINE=true: built-in dataset files are missing; "
            f"dataset={dataset_identifier}; "
            f"dataset_dir_name={dataset_dir_name}; "
            f"configured_dataset_dir={configured_dataset_dir}; "
            f"local_dataset_path={local_ds_root}; "
            f"missing_files=[{missing_list}]"
        )
        raise OfflineBuiltinDatasetMissingFiles(msg)

    log.info(
        "VDB_OFFLINE=true: using local built-in dataset files only; "
        "dataset=%s; local_dataset_path=%s; file_count=%s",
        dataset_identifier,
        local_ds_root,
        len(required_files),
    )


def verify_manager_local_dataset(dataset_identifier: str, manager, filters=None) -> None:
    from vectordb_bench import config

    verify_local_dataset_files(
        dataset_identifier=dataset_identifier,
        dataset_dir_name=manager.data.dir_name.lower(),
        files=expected_files_for_manager(manager, filters=filters),
        local_ds_root=manager.data_dir,
        configured_dataset_dir=config.DATASET_LOCAL_DIR,
    )


def patch_offline_builtin_dataset_readers() -> bool:
    if not offline_enabled():
        return False

    try:
        from vectordb_bench import config
        from vectordb_bench.backend.data_source import AliyunOSSReader, AwsS3Reader
    except ImportError:
        log.debug("VDB_OFFLINE=true but VDBBench dataset readers are not importable", exc_info=True)
        return False

    if getattr(AwsS3Reader, "_vdb_offline_patched", False) and getattr(
        AliyunOSSReader,
        "_vdb_offline_patched",
        False,
    ):
        return True

    def offline_init(self, *args, **kwargs):
        self._vdb_offline = True

    def offline_validate_file(self, remote, local) -> bool:
        return Path(local).is_file()

    def offline_read(self, dataset: str, files: list[str], local_ds_root: Path):
        dataset_identifier = dataset_identifier_from_dir_name(dataset)
        verify_local_dataset_files(
            dataset_identifier=dataset_identifier,
            dataset_dir_name=dataset,
            files=files,
            local_ds_root=Path(local_ds_root),
            configured_dataset_dir=config.DATASET_LOCAL_DIR,
        )

    for reader_class in (AwsS3Reader, AliyunOSSReader):
        reader_class.__init__ = offline_init
        reader_class.read = offline_read
        reader_class.validate_file = offline_validate_file
        reader_class._vdb_offline_patched = True

    log.info(
        "VDB_OFFLINE=true: patched AwsS3Reader and AliyunOSSReader to skip remote "
        "metadata validation and downloads; dataset_dir=%s",
        config.DATASET_LOCAL_DIR,
    )
    return True
