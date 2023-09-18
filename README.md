# pagecache_hit_miss


# Overview
This is a set of tools to monitor the memory used as pagecache.

For now it only has a tool which monitors the pagecache hit/miss

The idea is to add more tools, for example unify the pagecache_ttl (currently in an independent repo) 
https://github.com/sciclon2/pagecache_ttl


# Technical details
The cache hit and miss metric is gathered counting the kernel functions, following the Brendan Gregg idea 
https://www.brendangregg.com/blog/2014-12-31/linux-page-cache-hit-ratio.html

Using eBPF we track and cound the following Kernel functions:
* mark_page_accessed() for measuring cache accesses
* mark_buffer_dirty() for measuring cache writes
* add_to_page_cache_lru() for measuring page additions
* account_page_dirtied() for measuring page dirties


# Dependencies
This tool needs BCC, please follow the instructions bellow:
https://github.com/iovisor/bcc/blob/master/INSTALL.md


# Installation

Via pip:
```console
foo@bar:~# pip install pagecache_tools
```


Local in this repository root:
```console
foo@bar:~# pip install -e .
```

# Example


```console
foo@bar:~# /usr/local/bin/pagecache_hit_miss  --help
usage: pagecache_hit_miss [-h] [--interval-seconds INTERVAL_SECONDS]
                          [--daemon] [--send-metrics-to-dogstatsd]
                          [--log-level {INFO,DEBUG}] [--log-file LOG_FILE]

PageCache Hit/Miss

optional arguments:
  -h, --help            show this help message and exit
  --interval-seconds INTERVAL_SECONDS
                        Sets the interval to get the missed/hit values and
                        calculate the avg.
  --daemon              Execute the program in daemon mode.
  --send-metrics-to-dogstatsd
                        Send metrics to local DogStatsD
                        https://docs.datadoghq.com/developers/dogstatsd/
  --log-level {INFO,DEBUG}
                        Sets the log level
  --log-file LOG_FILE   Sets the log file.
```


