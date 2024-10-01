# hpc-libs

[![hpc-libs tests](https://github.com/charmed-hpc/hpc-libs/actions/workflows/ci.yaml/badge.svg)](https://github.com/charmed-hpc/hpc-libs/actions/workflows/ci.yaml)
[![Release](https://github.com/charmed-hpc/hpc-libs/actions/workflows/release-libs.yaml/badge.svg)](https://github.com/charmed-hpc/hpc-libs/actions/workflows/release-libs.yaml)
![GitHub License](https://img.shields.io/github/license/charmed-hpc/hpc-libs)
[![Matrix](https://img.shields.io/matrix/ubuntu-hpc%3Amatrix.org?logo=matrix&label=ubuntu-hpc)](https://matrix.to/#/#hpc:ubuntu.com)

A collection of charm libraries for authoring HPC charms 📖🖋️

The hpc-libs charm libraries are used within the [Juju](https://juju.is) charms that compose
Charmed HPC. They are standalone libraries, and should be managed
as charm libraries, with installation via `charmcraft fetch-lib ...`, after which they may be
imported and used as normal Python modules. The current charm libraries in hpc-libs include:

* `is_container` - a library for detecting the virtualization environment the charm is running within.
* `slurm_ops` - a library for managing Slurm cluster operations via snap or systemd.

## ✨ Getting Started

Each charm library contains documentation and usage information in its module-level docstring.
Pretty documentation, along with installation instructions, can be viewed on Charmhub:

* [`is_container` documentation](https://charmhub.io/hpc-libs/libraries/is_container)
* [`slurm_ops` documentation](https://charmhub.io/hpc-libs/libraries/slurm_ops)

## 🤔 What's next?

If you want to learn more about all the things you can do with the hpc-libs charm libraries,
or have any further questions on what you can do with the charm libraries, here are some
further resources for you to explore:

* [Open an issue](https://github.com/charmed-hpc/slurmutils/issues/new?title=ISSUE+TITLE&body=*Please+describe+your+issue*)
* [Ask a question on Github](https://github.com/orgs/charmed-hpc/discussions/categories/q-a)

## 🛠️ Development

This project uses [tox](https://tox.wiki) as its command runner, which provides
some useful commands that will help you while hacking on hpc-libs:

```shell
tox run -e fmt     # Apply formatting standards to code.
tox run -e lint    # Check code against coding style standards.
tox run -e static  # Run static type checks.
tox run -e unit    # Run unit tests.
```

To run the hpc-libs integration tests, you'll need to have both
[gambol](https://github.com/nuccitheboss/gambol) and [LXD](https://ubuntu.com/lxd) installed
on your machine:

```shell
tox run -e integration  # Run integration tests.
```

If you're interested in contributing your work to hpc-libs,
take a look at our [contributing guidelines](./CONTRIBUTING.md) for further details.

## 🤝 Project and community

The hpc-libs charm libraries are a project of the [Ubuntu High-Performance Computing community](https://ubuntu.com/community/governance/teams/hpc).
Interested in contributing bug fixes, new editors, documentation, or feedback? Want to join the Ubuntu HPC community? You’ve come to the right place 🤩

Here’s some links to help you get started with joining the community:

* [Ubuntu Code of Conduct](https://ubuntu.com/community/ethos/code-of-conduct)
* [Contributing guidelines](./CONTRIBUTING.md)
* [Join the conversation on Matrix](https://matrix.to/#/#hpc:ubuntu.com)
* [Get the latest news on Discourse](https://discourse.ubuntu.com/c/hpc/151)
* [Ask and answer questions on GitHub](https://github.com/orgs/charmed-hpc/discussions/categories/q-a)

## 📋 License

The hpc-libs charm libraries are free software, distributed under the Apache Software License, version 2.0.
See the [Apache-2.0 LICENSE](./LICENSE) file for further details.
