"""Feasibility prototype: one shared 8-GPU cluster, FIFO vs fair-share.

Both policies are strict: the job chosen next must start before any other job
(no backfilling), and running jobs are never paused (no preemption).
"""
import csv, math, random, sys
import simpy

TOTAL_GPUS = 8
HALF_LIFE_H = 24.0


class Job:
    def __init__(self, jid, user, submit, gpus, run):
        self.id, self.user, self.submit, self.gpus, self.run = jid, user, submit, gpus, run
        self.start = self.finish = None


def validate(rows):
    """Reject impossible jobs before the run (requirement F1)."""
    ok, rejected = [], []
    for r in rows:
        if not (1 <= r.gpus <= TOTAL_GPUS):
            rejected.append((r.id, f"asks for {r.gpus} GPUs; cluster has {TOTAL_GPUS}"))
        elif r.run <= 0 or r.submit < 0:
            rejected.append((r.id, "run time must be positive and submit time not negative"))
        else:
            ok.append(r)
    return ok, rejected


class Usage:
    """Decayed GPU-hours per user (half-life 24 h), updated at each event."""
    def __init__(self):
        self.u, self.last, self.running = {}, {}, {}

    def _advance(self, user, t):
        u, last, r = self.u.get(user, 0.0), self.last.get(user, 0.0), self.running.get(user, 0)
        dt = t - last
        if dt > 0:
            k = 0.5 ** (dt / HALF_LIFE_H)
            u = u * k + r * HALF_LIFE_H / math.log(2) * (1 - k)
        self.u[user], self.last[user] = u, t

    def change(self, user, t, delta_gpus):
        self._advance(user, t)
        self.running[user] = self.running.get(user, 0) + delta_gpus

    def value(self, user, t):
        self._advance(user, t)
        return self.u[user]


def fair_share_factors(queue, running_users, usage, t):
    """F = 2^(-U/S) for every active user.
    Active user: has at least one job waiting or running at time t.
    S = 1 / number of active users. U = user's decayed GPU-hours divided by the
    total decayed GPU-hours of all active users (0 for everyone if the total is 0)."""
    active = sorted({j.user for j in queue} | running_users)
    S = 1.0 / len(active)
    raw = {a: usage.value(a, t) for a in active}
    total = sum(raw.values())
    F = {}
    for a in active:
        U = raw[a] / total if total > 0 else 0.0
        F[a] = 2 ** (-U / S)
    return F, S, raw


def pick_next(policy, queue, running_users, usage, t, log):
    if policy == "fifo":
        return min(queue, key=lambda j: (j.submit, j.id))
    F, S, raw = fair_share_factors(queue, running_users, usage, t)
    if log is not None:
        log.append((t, {a: round(F[a], 3) for a in F}))
    return max(queue, key=lambda j: (F[j.user], -j.submit, -j.id))


def simulate(jobs, policy, decision_log=None):
    env = simpy.Environment()
    state = {"free": TOTAL_GPUS, "max_in_use": 0, "pending": False}
    queue, running, usage, events = [], {}, Usage(), []

    def try_start():
        while queue:
            j = pick_next(policy, queue, {u for u, n in running.items() if n}, usage, env.now, decision_log)
            if j.gpus > state["free"]:
                return  # strict order: chosen job waits, nothing jumps ahead
            queue.remove(j)
            state["free"] -= j.gpus
            state["max_in_use"] = max(state["max_in_use"], TOTAL_GPUS - state["free"])
            assert state["free"] >= 0, "C1 violated"
            j.start = env.now
            usage.change(j.user, env.now, j.gpus)
            running[j.user] = running.get(j.user, 0) + 1
            events.append(("start", j.id))
            env.process(run_job(j))

    def schedule_soon():
        # run the decision after every event at this same instant has been processed
        if not state["pending"]:
            state["pending"] = True
            def p():
                yield env.timeout(0)
                state["pending"] = False
                try_start()
            env.process(p())

    def run_job(j):
        yield env.timeout(j.run)
        state["free"] += j.gpus
        usage.change(j.user, env.now, -j.gpus)
        running[j.user] -= 1
        j.finish = env.now
        events.append(("finish", j.id))
        schedule_soon()

    def arrive(j):
        yield env.timeout(j.submit)
        queue.append(j)
        schedule_soon()

    for j in jobs:
        env.process(arrive(j))
    env.run()
    return state, events


def check_and_report(jobs, policy, state, events):
    ids = {j.id for j in jobs}
    starts = [e[1] for e in events if e[0] == "start"]
    done = [e[1] for e in events if e[0] == "finish"]
    c2 = (set(done) == ids and len(done) == len(ids) and len(set(starts)) == len(starts)
          and all(j.start >= j.submit for j in jobs))
    makespan = max(j.finish for j in jobs) - min(j.submit for j in jobs)
    busy = sum(j.gpus * j.run for j in jobs)
    util = busy / (TOTAL_GPUS * makespan)
    users = sorted({j.user for j in jobs})
    per = {}
    for u in users:
        mine = [j for j in jobs if j.user == u]
        waits = [j.start - j.submit for j in mine]
        slows = [(j.finish - j.submit) / j.run for j in mine]
        per[u] = dict(max_wait=max(waits), avg_wait=sum(waits) / len(waits),
                      max_slow=max(slows), avg_slow=sum(slows) / len(slows))
    x = [per[u]["avg_slow"] for u in users]
    jain = sum(x) ** 2 / (len(x) * sum(v * v for v in x))
    return dict(policy=policy, c1=state["max_in_use"] <= TOTAL_GPUS, max_in_use=state["max_in_use"],
                c2=c2, makespan=makespan, util=util, jain=jain, per=per)


def burst():
    jobs = [Job(i, "Ben", 0.0, 4, 6.0) for i in range(1, 21)]
    jobs.append(Job(21, "Ana", 5 / 60, 1, 0.5))
    jobs += [Job(22, "Chen", 1.0, 2, 3.0), Job(23, "Chen", 1.0, 2, 3.0)]
    return jobs


def random_workload(kind, seed):
    rng = random.Random(seed)
    jobs, jid = [], 1
    def add(user, n, t0, t1):
        nonlocal jid
        for _ in range(n):
            jobs.append(Job(jid, user, round(rng.uniform(t0, t1), 2), rng.choice([1, 2, 4]),
                            rng.choice([0.5, 1, 2, 4, 6])))
            jid += 1
    if kind == "balanced":
        for u in ("Ana", "Ben", "Chen"):
            add(u, 10, 0, 24)
    else:  # one heavy user
        add("Ben", 30, 0, 2)
        add("Ana", 5, 0, 24)
        add("Chen", 5, 0, 24)
    return jobs


def fresh(jobs):
    return [Job(j.id, j.user, j.submit, j.gpus, j.run) for j in jobs]


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "results.txt"
    lines = []
    p = lines.append

    # F1: invalid input is rejected
    ok, rej = validate([Job(99, "Ana", 0, 10, 1.0), Job(100, "Ana", 0, 1, -1.0), Job(101, "Ana", 0, 1, 1.0)])
    p(f"F1 rejected: {rej}; accepted: {[j.id for j in ok]}")

    # C1 fixture: two jobs fit alone (4 free) but not together, ready at the same moment
    fx = [Job(1, "Ben", 0, 4, 1.0), Job(2, "Ana", 0.5, 4, 1.0), Job(3, "Chen", 0.5, 4, 1.0)]
    for pol in ("fifo", "fair"):
        js = fresh(fx); st, ev = simulate(js, pol)
        p(f"C1 fixture {pol}: max GPUs in use {st['max_in_use']}; starts "
          + ", ".join(f"job{j.id}@{j.start}h" for j in js))

    # Burst workload
    p("\nBURST WORKLOAD (Ben 20x4GPU 6h @0, Ana 1x1GPU 0.5h @0:05, Chen 2x2GPU 3h @1:00)")
    burst_res = {}
    for pol in ("fifo", "fair"):
        js = fresh(burst()); log = []
        st, ev = simulate(js, pol, log)
        r = check_and_report(js, pol, st, ev); burst_res[pol] = r
        p(f"\n[{pol}] C1 ok={r['c1']} (max in use {r['max_in_use']}), C2 ok={r['c2']}, "
          f"total completion time {r['makespan']:.2f} h, utilization {r['util']*100:.1f}%, Jain {r['jain']:.3f}")
        for u, v in r["per"].items():
            p(f"   {u:5s} longest wait {v['max_wait']:6.2f} h  avg wait {v['avg_wait']:6.2f} h  "
              f"max slowdown {v['max_slow']:6.2f}  avg slowdown {v['avg_slow']:6.2f}")
        if pol == "fair":
            first = [e for e in log if e[0] >= 5.99][:1]
            p(f"   first decision at t=6h, fair-share factors: {first}")
        p("   starts: " + ", ".join(f"{j.user[0]}{j.id}@{j.start:.2f}" for j in sorted(js, key=lambda j: (j.start, j.id))[:8]) + " ...")
    # Determinism (F5)
    a = check_and_report(*(lambda js: (js, "fair", *simulate(js, "fair")))(fresh(burst())))
    b = check_and_report(*(lambda js: (js, "fair", *simulate(js, "fair")))(fresh(burst())))
    p(f"\nF5 repeat run identical: {a == b}")

    # Random workloads, 10 seeds
    for kind in ("balanced", "heavy"):
        p(f"\n{kind.upper()} WORKLOAD, seeds 1-10 (worst user's max slowdown / worst longest wait / total completion time)")
        for seed in range(1, 11):
            row = []
            for pol in ("fifo", "fair"):
                js = fresh(random_workload(kind, seed)); st, ev = simulate(js, pol)
                r = check_and_report(js, pol, st, ev)
                assert r["c1"] and r["c2"]
                row.append((max(v["max_slow"] for v in r["per"].values()),
                            max(v["max_wait"] for v in r["per"].values()), r["makespan"]))
            (fs, fw, fm), (ss, sw, sm) = row
            p(f"  seed {seed:2d}: FIFO {fs:6.2f} / {fw:6.2f} h / {fm:6.2f} h   FAIR {ss:6.2f} / {sw:6.2f} h / {sm:6.2f} h"
              f"   slowdown cut {100*(1-ss/fs):5.1f}%  completion change {100*(sm/fm-1):+5.1f}%")

    open(out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
