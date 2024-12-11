# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Constants used within unit tests for the `slurm_ops` charm library."""

import grp
import os
import pwd

FAKE_USER_UID = os.getuid()
FAKE_USER_NAME = pwd.getpwuid(FAKE_USER_UID).pw_name
FAKE_GROUP_GID = os.getgid()
FAKE_GROUP_NAME = grp.getgrgid(FAKE_GROUP_GID).gr_name

SNAP_SLURM_INFO = """
name:      slurm
summary:   "Slurm: A Highly Scalable Workload Manager"
publisher: –
store-url: https://snapcraft.io/slurm
license:   Apache-2.0
description: |
    Slurm is an open source, fault-tolerant, and highly scalable cluster
    management and job scheduling system for large and small Linux clusters.
commands:
    - slurm.command1
    - slurm.command2
services:
    slurm.logrotate:                 oneshot, enabled, inactive
    slurm.munged:                    simple, enabled, active
    slurm.slurm-prometheus-exporter: simple, disabled, inactive
    slurm.slurmctld:                 simple, disabled, active
    slurm.slurmd:                    simple, enabled, active
    slurm.slurmdbd:                  simple, disabled, active
    slurm.slurmrestd:                simple, disabled, active
channels:
    latest/stable:    –
    latest/candidate: 23.11.7 2024-06-26 (460) 114MB classic
    latest/beta:      ↑
    latest/edge:      23.11.7 2024-06-26 (459) 114MB classic
installed:          23.11.7             (x1) 114MB classic
"""

SNAP_SLURM_INFO_NOT_INSTALLED = """
name:      slurm
summary:   "Slurm: A Highly Scalable Workload Manager"
publisher: –
store-url: https://snapcraft.io/slurm
license:   Apache-2.0
description: |
    Slurm is an open source, fault-tolerant, and highly scalable cluster
    management and job scheduling system for large and small Linux clusters.
channels:
    latest/stable:    –
    latest/candidate: 23.11.7 2024-06-26 (460) 114MB classic
    latest/beta:      ↑
    latest/edge:      23.11.7 2024-06-26 (459) 114MB classic
"""

APT_SLURM_INFO = """Desired=Unknown/Install/Remove/Purge/Hold
| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
||/ Name           Version          Architecture Description
+++-==============-================-============-=================================
ii  slurmctld      23.11.7-2ubuntu1 amd64        SLURM central management daemon
"""

ULIMIT_CONFIG = """
* soft nofile  1048576
* hard nofile  1048576
* soft memlock unlimited
* hard memlock unlimited
* soft stack unlimited
* hard stack unlimited
"""

MUNGEKEY_BASE64 = b"MTIzNDU2Nzg5MA=="

JWT_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAt3PLWkwUOeckDwyMpHgGqmOZhitC8KfOQY/zPWfo+up5RQXz
gVWqsTIt1RWynxIwCGeKYfVlhoKNDEDL1ZjYPcrrGBgMEC8ifqxkN4RC8bwwaGrJ
9Zf0kknPHI5AJ9Fkv6EjgAZW1lwV0uEE5kf0wmlgfThXfzwwGVHVwemE1EgUzdI/
rVxFP5Oe+mRM7kWdtXQrfizGhfmr8laCs+dgExpPa37mk7u/3LZfNXXSWYiaNtie
vax5BxmI4bnTIXxdTT4VP9rMxG8nSspVj5NSWcplKUANlIkMKiO7k/CCD/YzRzM0
0yZttiTvECG+rKy+KJd97dbtj6wSvbJ7cjfq2wIDAQABAoIBACNTfPkqZUqxI9Ry
CjMxmbb97vZTJlTJO4KMgb51X/vRYwDToIxrPq9YhlLeFsNi8TTtG0y5wI8iXJ7b
a2T6RcnAZX0CRHBpYy8Za0L1iR6bqoaw6asNU99Hr0ZEbj48qDXuhbOFhPtKSDmP
cy4U9SDqwdXbH540rN5zT8JDgXyPAVJpwgsShk7rhgOFGIPIZqQoxEjPV3jr1sbk
k7c39fJR6Kxywppn7flSmNX3v1LDu4NDIp0Llt1NlcKlbdy5XWEW9IbiIYi3JTpB
kMpkFQFIuUyledeFyVFPsP8O7Da2rZS6Fb1dYNWzh3WkDRiAwYgTspiYiSf4AAi4
TgrOmiECgYEA312O5bXqXOapU+S2yAFRTa8wkZ1iRR2E66NypZKVsv/vfe0bO+WQ
kI6MRmTluvOKsKe3JulJZpjbl167gge45CHnFPZxEODAJN6OYp+Z4aOvTYBWQPpO
A75AGSheL66PWe4d+ZGvxYCZB5vf4THAs8BsGlFK04RKL1vHADkUjHUCgYEA0kFh
2ei/NP8ODrwygjrpjYSc2OSH9tBUoB7y5zIfLsXshb3Fn4pViF9vl01YkJJ57kki
KQm7rgqCsFnKS4oUFbjDDFbo351m1e3XRbPAATIiqtJmtLoLoSWuhXpsCbneM5bB
xLhFmm8RcFC6ORPBE2WMTGYzTEKydhImvUo+8A8CgYEAssWpyjaoRgSjP68Nj9Rm
Izv1LoZ9kX3H1eUyrEw/Hk3ze6EbK/xXkStWID0/FTs5JJyHXVBX3BK5plQ+1Rqj
I4vy7Hc2FWEcyCWMZmkA+3RLqUbvQgBUEnDh0oDZqWYX+802FnpA6V08nbdnH1D3
v6Zhn0qzDcmSqobVJluJE8UCgYB93FO1/QSQtel1WqUlnhx28Z5um4bkcVtnKn+f
dDqEZkiq2qn1UfrXksGbIdrVWEmTIcZIKKJnkbUf2fAl/fb99ccUmOX4DiIkB6co
+2wBi0CDX0XKA+C4S3VIQ7tuqwvfd+xwVRqdUsVupXSEfFXExbIRfdBRY0+vLDhy
cYJxcwKBgQCK+dW+F0UJTQq1rDxfI0rt6yuRnhtSdAq2+HbXNx/0nwdLQg7SubWe
1QnLcdjnBNxg0m3a7S15nyO2xehvB3rhGeWSfOrHYKJNX7IUqluVLJ+lIwgE2eAz
94qOCvkFCP3pnm/MKN6/rezyOzrVJn7GbyDhcjElu+DD+WRLjfxiSw==
-----END RSA PRIVATE KEY-----
"""

EXAMPLE_ACCT_GATHER_CONFIG = """#
# `acct_gather.conf` file generated at 2024-09-18 15:10:44.652017 by slurmutils.
#
EnergyIPMIFrequency=1
EnergyIPMICalcAdjustment=yes
EnergyIPMIPowerSensors=Node=16,19;Socket1=19,26;KNC=16,19
EnergyIPMIUsername=testipmiusername
EnergyIPMIPassword=testipmipassword
EnergyIPMITimeout=10
ProfileHDF5Dir=/mydir
ProfileHDF5Default=ALL
ProfileInfluxDBDatabase=acct_gather_db
ProfileInfluxDBDefault=ALL
ProfileInfluxDBHost=testhostname
ProfileInfluxDBPass=testpassword
ProfileInfluxDBRTPolicy=testpolicy
ProfileInfluxDBUser=testuser
ProfileInfluxDBTimeout=10
InfinibandOFEDPort=0
SysfsInterfaces=enp0s1
"""

EXAMPLE_CGROUP_CONFIG = """#
# `cgroup.conf` file generated at 2024-09-18 15:10:44.652017 by slurmutils.
#
ConstrainCores=yes
ConstrainDevices=yes
ConstrainRAMSpace=yes
ConstrainSwapSpace=yes
"""

EXAMPLE_GRES_CONFIG = """#
# `gres.conf` file generated at 2024-12-10 14:17:35.161642 by slurmutils.
#
AutoDetect=nvml
Name=gpu Type=gp100  File=/dev/nvidia0 Cores=0,1
Name=gpu Type=gp100  File=/dev/nvidia1 Cores=0,1
Name=gpu Type=p6000  File=/dev/nvidia2 Cores=2,3
Name=gpu Type=p6000  File=/dev/nvidia3 Cores=2,3
Name=mps Count=200  File=/dev/nvidia0
Name=mps Count=200  File=/dev/nvidia1
Name=mps Count=100  File=/dev/nvidia2
Name=mps Count=100  File=/dev/nvidia3
Name=bandwidth Type=lustre Count=4G Flags=CountOnly

NodeName=juju-c9c6f-[1-10] Name=gpu Type=rtx File=/dev/nvidia[0-3] Count=8G
"""

EXAMPLE_SLURM_CONFIG = """#
# `slurm.conf` file generated at 2024-01-30 17:18:36.171652 by slurmutils.
#
SlurmctldHost=juju-c9fc6f-0(10.152.28.20)
SlurmctldHost=juju-c9fc6f-1(10.152.28.100)

ClusterName=charmed-hpc
AuthType=auth/munge
Epilog=/usr/local/slurm/epilog
Prolog=/usr/local/slurm/prolog
FirstJobId=65536
InactiveLimit=120
JobCompType=jobcomp/filetxt
JobCompLoc=/var/log/slurm/jobcomp
KillWait=30
MaxJobCount=10000
MinJobAge=3600
PluginDir=/usr/local/lib:/usr/local/slurm/lib
ReturnToService=0
SchedulerType=sched/backfill
SlurmctldLogFile=/var/log/slurm/slurmctld.log
SlurmdLogFile=/var/log/slurm/slurmd.log
SlurmctldPort=7002
SlurmdPort=7003
SlurmdSpoolDir=/var/spool/slurmd.spool
StateSaveLocation=/var/spool/slurm.state
SwitchType=switch/none
TmpFS=/tmp
WaitTime=30

#
# Node configurations
#
NodeName=juju-c9fc6f-2 NodeAddr=10.152.28.48 CPUs=1 RealMemory=1000 TmpDisk=10000
NodeName=juju-c9fc6f-3 NodeAddr=10.152.28.49 CPUs=1 RealMemory=1000 TmpDisk=10000
NodeName=juju-c9fc6f-4 NodeAddr=10.152.28.50 CPUs=1 RealMemory=1000 TmpDisk=10000
NodeName=juju-c9fc6f-5 NodeAddr=10.152.28.51 CPUs=1 RealMemory=1000 TmpDisk=10000

#
# Down node configurations
#
DownNodes=juju-c9fc6f-5 State=DOWN Reason="Maintenance Mode"

#
# Partition configurations
#
PartitionName=DEFAULT MaxTime=30 MaxNodes=10 State=UP
PartitionName=batch Nodes=juju-c9fc6f-2,juju-c9fc6f-3,juju-c9fc6f-4,juju-c9fc6f-5 MinNodes=4 MaxTime=120 AllowGroups=admin
"""

EXAMPLE_SLURMDBD_CONFIG = """#
# `slurmdbd.conf` file generated at 2024-01-30 17:18:36.171652 by slurmutils.
#
ArchiveEvents=yes
ArchiveJobs=yes
ArchiveResvs=yes
ArchiveSteps=no
ArchiveTXN=no
ArchiveUsage=no
ArchiveScript=/usr/sbin/slurm.dbd.archive
AuthInfo=/var/run/munge/munge.socket.2
AuthType=auth/munge
AuthAltTypes=auth/jwt
AuthAltParameters=jwt_key=16549684561684@
DbdHost=slurmdbd-0
DbdBackupHost=slurmdbd-1
DebugLevel=info
PluginDir=/all/these/cool/plugins
PurgeEventAfter=1month
PurgeJobAfter=12month
PurgeResvAfter=1month
PurgeStepAfter=1month
PurgeSuspendAfter=1month
PurgeTXNAfter=12month
PurgeUsageAfter=24month
LogFile=/var/log/slurmdbd.log
PidFile=/var/run/slurmdbd.pid
SlurmUser=slurm
StoragePass=supersecretpasswd
StorageType=accounting_storage/mysql
StorageUser=slurm
StorageHost=127.0.0.1
StoragePort=3306
StorageLoc=slurm_acct_db
"""
