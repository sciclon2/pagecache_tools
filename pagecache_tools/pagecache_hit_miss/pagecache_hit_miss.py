import logging
from time import sleep

from bcc import BPF
from datadog import initialize, statsd

logger = logging.getLogger(__name__)


class PageCacheHitMiss(object):
    def __init__(
        self,
        interval_seconds,
        logfile,
        send_metrics_to_dogstatsd=False,
    ):
        self.interval_seconds = interval_seconds
        self.logfile = logfile
        self.send_metrics_to_dogstatsd = send_metrics_to_dogstatsd

        if send_metrics_to_dogstatsd:
            self.dogstatsd_options = {"statsd_host": "127.0.0.1", "statsd_port": 8125}
            initialize(**self.dogstatsd_options)
            self.dogstatsd_metric_name = "pagecache_ttl.min_cached_time_seconds"
            self.statsd = statsd

    def _attach_kprobes_and_tracepoints(self, ebpf):
        ebpf.attach_kprobe(event="add_to_page_cache_lru", fn_name="do_count_apcl")
        ebpf.attach_kprobe(event="mark_page_accessed", fn_name="do_count_mpa")
        ebpf.attach_kprobe(event="mark_buffer_dirty", fn_name="do_count_mbd")

        # Function account_page_dirtied() is changed to folio_account_dirtied() in 5.15.
        # Both folio_account_dirtied() and account_page_dirtied() are
        # static functions and they may be gone during compilation and this may
        # introduce some inaccuracy, use tracepoint writeback_dirty_{page,folio},
        # instead when attaching kprobe fails, and report the running error in time.
        if BPF.get_kprobe_functions(b"folio_account_dirtied"):
            ebpf.attach_kprobe(event="folio_account_dirtied", fn_name="do_count_apd")
        elif BPF.get_kprobe_functions(b"account_page_dirtied"):
            ebpf.attach_kprobe(event="account_page_dirtied", fn_name="do_count_apd")
        elif BPF.tracepoint_exists("writeback", "writeback_dirty_folio"):
            ebpf.attach_tracepoint(
                tp="writeback:writeback_dirty_folio", fn_name="do_count_apd_tp"
            )
        elif BPF.tracepoint_exists("writeback", "writeback_dirty_page"):
            ebpf.attach_tracepoint(
                tp="writeback:writeback_dirty_page", fn_name="do_count_apd_tp"
            )
        else:
            raise Exception(
                "Failed to attach kprobe %s or %s or any tracepoint"
                % ("folio_account_dirtied", "account_page_dirtied")
            )

    def _get_hit_ratio(self, counts):
        mpa = 0
        mbd = 0
        apcl = 0
        apd = 0
        for k, v in counts.items():
            if k.nf == 0:  # NF_APCL
                apcl = max(0, v.value)
            if k.nf == 1:  # NF_MPA
                mpa = max(0, v.value)
            if k.nf == 2:  # NF_MBD
                mbd = max(0, v.value)
            if k.nf == 3:  # NF_APD
                apd = max(0, v.value)

        # total = total cache accesses without counting dirties
        # misses = total of add to lru because of read misses
        total = mpa - mbd
        misses = apcl - apd
        if misses < 0:
            misses = 0
        if total < 0:
            total = 0
        hits = total - misses

        # If hits are < 0, then its possible misses are overestimated
        # due to possibly page cache read ahead adding more pages than
        # needed. In this case just assume misses as total and reset hits.
        if hits < 0:
            misses = total
            hits = 0
        ratio = 0
        if total > 0:
            ratio = float(hits) / total

        return ratio * 100

    def run(self):
        """
        Main loop which will live until the process gets a Signal
        """
        bpf = BPF(text=BPF_TEXT)
        self._attach_kprobes_and_tracepoints(bpf)

        while True:
            sleep(self.interval_seconds)
            counts = bpf.get_table("counts")
            # counts = bpf["counts"]

            hit_ratio = self._get_hit_ratio(counts)
            counts.clear()
            print(hit_ratio)


BPF_TEXT = """
#include <uapi/linux/ptrace.h>
struct key_t {
    // NF_{APCL,MPA,MBD,APD}
    u32 nf;
};

enum {
    NF_APCL,
    NF_MPA,
    NF_MBD,
    NF_APD,
};

BPF_HASH(counts, struct key_t);

static int __do_count(void *ctx, u32 nf) {
    struct key_t key = {};
    u64 ip;

    key.nf = nf;
    counts.atomic_increment(key); // update counter
    return 0;
}

int do_count_apcl(struct pt_regs *ctx) {
    return __do_count(ctx, NF_APCL);
}
int do_count_mpa(struct pt_regs *ctx) {
    return __do_count(ctx, NF_MPA);
}
int do_count_mbd(struct pt_regs *ctx) {
    return __do_count(ctx, NF_MBD);
}
int do_count_apd(struct pt_regs *ctx) {
    return __do_count(ctx, NF_APD);
}
int do_count_apd_tp(void *ctx) {
    return __do_count(ctx, NF_APD);
}
"""
