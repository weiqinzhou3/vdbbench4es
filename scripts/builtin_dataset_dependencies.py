import importlib.util


REQUIRED_BUILTIN_DATASET_MODULES = {
    "oss2": "oss2",
    "aliyunsdkcore": "aliyun-python-sdk-core",
    "cryptography": "cryptography",
    "cffi": "cffi",
    "_cffi_backend": "cffi",
}


class BuiltinDatasetDependencyError(RuntimeError):
    pass


def ensure_builtin_dataset_dependencies():
    missing = [
        package
        for module, package in REQUIRED_BUILTIN_DATASET_MODULES.items()
        if importlib.util.find_spec(module) is None
    ]

    if not missing:
        return

    unique_missing = sorted(set(missing))
    raise BuiltinDatasetDependencyError(
        "Builtin dataset preparation requires additional download/crypto "
        "dependencies. Missing package/module: "
        f"{', '.join(unique_missing)}. "
        "Install or refresh dependencies with: "
        "python3 -m pip install -r requirements.txt. "
        "If '_cffi_backend' is missing, reinstall cffi in the active virtual "
        "environment: python3 -m pip install --force-reinstall cffi."
    )
