# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This changelog was introduced after earlier releases, so versions before `0.10.0`
are not backfilled here.

## [Unreleased]

### Added
- Introduced `--install-menu` and `--uninstall-menu` to manage the Windows File Explorer context-menu entry.
- Prompted for the canonical path when only the input folder was supplied.
- Prompted to create a missing canonical path before linking.

### Changed
- Split the CLI implementation into `zerolink.cli` and kept `zerolink.__main__` as the executable wrapper.
- Updated the package metadata to describe Zerolink as a one-step `rclone` and symlink workflow.

### Fixed
- Kept packaged Windows launches open after unhandled errors so tracebacks remained visible.
- Resolved `--version` through `zerolink.__version__` with a metadata fallback.
