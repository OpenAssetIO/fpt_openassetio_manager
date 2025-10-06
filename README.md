# FPT OpenAssetIO Manager

An [OpenAssetIO](https://github.com/OpenAssetIO/OpenAssetIO) manager
plugin for [Flow Production Tracking](https://www.autodesk.com/products/flow-production-tracking/overview)
(formerly ShotGrid/Shotgun).

## Overview

This plugin provides OpenAssetIO integration with Flow Production
Tracking, allowing applications to interact with FPT assets through the
OpenAssetIO interface.

Flow Production Tracking (FPT) is highly configurable, and its usage is
likely to vary wildly between facilities. As such, this OpenAssetIO
plugin should be viewed as a starter/example/template plugin, that can
be customised for a facility's bespoke FPT configuration.

## Requirements

The plugin is known to work with

- Python 3.10
- [OpenAssetIO](https://github.com/OpenAssetIO/OpenAssetIO) 1.0.0-rc.1.0
- [OpenAssetIO-MediaCreation](https://github.com/OpenAssetIO/OpenAssetIO-MediaCreation)
  1.0.0-alpha.11
- [Flow Production Tracking Python API](https://github.com/shotgunsoftware/python-api)
  3.3
- (Optional) [Flow Production Tracking Core API](https://github.com/shotgunsoftware/tk-core)
  0.21 - required for resolving workfiles.

## Installation

From the project root:

```bash
python -m pip install .
```

Note that this will install all dependencies, including `openassetio`,
`openassetio-mediacreation` and `shotgun_api3`, which may already be
available (and potentially different versions) in the host application
environment.

An alternative for environments that already include all dependencies
is to add the `plugin` directory in this repository to the
`OPENASSETIO_PLUGIN_PATH` environment variable; and the `plugin/ui`
directory to the `OPENASSETIO_UI_PLUGIN_PATH` environment variable.

## Configuration

See the [OpenAssetIO documentation](https://docs.openassetio.org/OpenAssetIO/runtime_configuration.html)
for general instructions on host application configuration.

See the [example config file](./docs/example_openassetio_config.toml)
for available settings.

There are three broad modes of operation, explained the following
subsections.

### As part of a generic standalone application

This is the most basic mode of operation.

It requires the standalone `shotgun_api3` Python package to be
installed.

Authentication credentials must be configured in the OpenAssetIO
configuration.

Metadata can then be resolved from a remote FPT instance. However,
workfile metadata (i.e. paths) cannot be resolved, since these exist
only on disk and not in the FPT database. See the following subsections
for options that allow workfiles to be resolved.

### As part of an FPT project-specific standalone application

This is perhaps the most flexible mode of operation. The Python
environment must have access to a configured FPT toolkit, i.e.
`PYTHONPATH` must contain a `/path/to/fpt/conf/install/core/python`-like
directory.

Authentication credentials must be configured in the OpenAssetIO
configuration.

In addition, a project ID must be given in the OpenAssetIO
configuration, providing the pipeline configuration to use for resolving
workfiles.

Metadata from both a remote FPT instance and workfiles can then be
resolved.

### As part of an FPT application integration

Typically, this would be an application launched through the Flow
Production Tracking Desktop launcher.

The launcher and ["engine"](https://help.autodesk.com/view/SGDEV/ENU/?guid=SGD_si_integrations_engine_supported_versions_html)
(e.g. tk-nuke) handles authentication and configures the Python
environment, meaning the OpenAssetIO configuration does not require any
authentication credentials or project ID.

Metadata from both a remote FPT instance and workfiles can then be
resolved, in the context of the launched application engine.

## Entity References

Entity references use two formats.

Entities that exist as records in the FPT database can be referenced
using

```
fpt://asset/{object_type}/{object_id}
```

For example, `fpt://asset/PublishedFile/123`.

Workfiles, a special case of entities that exist only on disk, may not
have a corresponding FPT database entry. These can be referenced using

```
fpt://workfile/{template_name}/{field_1}/{field_2}/...
```

where the `template_name` is the name of an FPT file path template, and
`field_1`, `field_2`, etc., are the fields required to fill in that
template, in the correct order.

## Current Status

This is the first iteration of the plugin with minimal functionality:

- [x] Authentication via Script keys.
- [x] Authentication via Legacy Login username/password.
- [x] Authentication via Shotgun Desktop.
- [ ] Authentication via Personal Access Token.
- [ ] Authentication via web login.
- [x] Resolving paths to PublishedFile objects.
- [ ] Resolving other metadata - _partial support - e.g. frame range,
  name, Version path/URL_.
- [x] Resolving paths to workfiles.
- [ ] Querying related entities.
- [ ] Publishing.
- [x] UI delegation.

## Development

### Running Tests

The tests make use of the OpenAssetIO [API Compliance Test Harness](https://docs.openassetio.org/OpenAssetIO/testing.html).

The required test fixtures are facility-dependent, and so several
environment variables must be provided for use by the tests.

* `OPENASSETIO_TEST_SERVER_URL` - the FPT server to use for tests.
* For authentication, either set
    - `OPENASSETIO_TEST_SCRIPT_NAME` and `OPENASSETIO_TEST_API_KEY` to
      an FPT [API Script](https://help.autodesk.com/view/SGDEV/ENU/?guid=SGD_py_python_api_create_manage_html)
      name and key, respectively; or
    - `OPENASSETIO_TEST_LEGACY_USER` and
      `OPENASSETIO_TEST_LEGACY_PASSWORD` to the login and password of
      FPT [Legacy Login Credentials](https://help.autodesk.com/view/SGSUB/ENU/?guid=SG_Administrator_ar_manage_accounts_ar_account_settings_after_migrating_html#legacy-login-and-personal-access-token-settings),
      respectively.
* `OPENASSETIO_TEST_EXISTING_PUBLISHEDFILE_ID` - the numeric ID of an
  existing PublishedFile object
* `OPENASSETIO_TEST_MISSING_PUBLISHEDFILE_ID` - the numeric ID of a
  non-existent PublishedFile object.
* For workfile tests (optional)
    - `PYTHONPATH` - ensure this contains the path to an installation of
      FPT Toolkit Core, e.g. `/path/to/fpt/conf/install/core/python`.
    - `OPENASSETIO_TEST_PROJECT_ID` - the numeric ID of a project from
      which to retrieve pipeline configuration.
    - `OPENASSETIO_TEST_WORKFILE_TEMPLATE_NAME` - the name of a file
      path template to use in tests.
    - `OPENASSETIO_TEST_WORKFILE_TEMPLATE_FIELDS` - fields required to
      fill in the above path template, in order, `/`-delimited.


The test harness tests are conveniently wrapped in `pytest`:

```bash
python -m pip install . -r tests/requirements.txt
python -m pytest tests
```

### Linting

The plugin and tests conform to the pylint linter, configured through
the `pyproject.toml` file. To run `pylint`

```bash
python -m pip install -r tests/requirements.txt
python -m pylint --rcfile pyproject.toml plugin tests
```

## License

Apache-2.0 - See [LICENSE](./LICENSE) file for details.

### A note on Flow Production Tracking

This project does not bundle or embed commercial components, but it does
provide interoperability with commercial components. The licences terms
of dependencies related to this are linked below for convenience:

- Flow Production Tracking Python API: [LICENSE](https://github.com/shotgunsoftware/python-api/blob/master/LICENSE)
- (An optional dependency) Flow Production Tracking Core API:
  [SHOTGUN PIPELINE TOOLKIT SOURCE CODE LICENSE](https://github.com/shotgunsoftware/tk-core?tab=License-1-ov-file#readme)

## Contributing

Please feel free to contribute pull requests or issues. Note that
contributions will require signing a CLA.

See the OpenAssetIO contribution docs for how to structure
[commit messages](https://github.com/OpenAssetIO/OpenAssetIO/blob/main/doc/contributing/COMMITS.md),
the [pull request process](https://github.com/OpenAssetIO/OpenAssetIO/blob/main/doc/contributing/PULL_REQUESTS.md),
and [coding style guide](https://github.com/OpenAssetIO/OpenAssetIO/blob/main/doc/contributing/CODING_STYLE.md).
