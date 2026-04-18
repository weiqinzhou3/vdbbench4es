import os


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


def parse_env_bool(name, default=False):
    value = os.getenv(name)
    if value is None or value == "":
        return default

    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False

    raise ValueError(
        f"{name} must be one of: {', '.join(sorted(TRUE_VALUES | FALSE_VALUES))}"
    )


def get_es_hosts():
    hosts = os.getenv("ES_HOSTS", "http://localhost:9200").split(",")
    return [host.strip() for host in hosts if host.strip()]


def resolve_ssl_show_warn(verify_certs):
    explicit_show_warn = os.getenv("ES_SSL_SHOW_WARN")
    if explicit_show_warn is not None and explicit_show_warn != "":
        return parse_env_bool("ES_SSL_SHOW_WARN")

    suppress_warning = os.getenv("ES_SUPPRESS_INSECURE_WARNING")
    if suppress_warning is not None and suppress_warning != "":
        return not parse_env_bool("ES_SUPPRESS_INSECURE_WARNING")

    return bool(verify_certs)


def configure_insecure_request_warning(verify_certs, ssl_show_warn):
    if verify_certs or ssl_show_warn:
        return

    try:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except ImportError:
        pass


def build_elasticsearch_options(include_auth=True):
    verify_certs = parse_env_bool("ES_VERIFY_CERTS", default=False)
    ssl_show_warn = resolve_ssl_show_warn(verify_certs)
    configure_insecure_request_warning(
        verify_certs=verify_certs,
        ssl_show_warn=ssl_show_warn,
    )

    options = {
        "hosts": get_es_hosts(),
        "verify_certs": verify_certs,
        "ssl_show_warn": ssl_show_warn,
    }

    if include_auth:
        user = os.getenv("ES_USER", "elastic")
        password = os.getenv("ES_PASSWORD", "")
        if user and password:
            options["basic_auth"] = (user, password)

    return options
