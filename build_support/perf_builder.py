#!/usr/bin/python
import datetime
import os
import json
import yaml
import random
from . import ProjectMap, Options, RevisionSpecification, run_batch_command, Export, check_gpu_hang

class PerfBuilder(object):
    def __init__(self, benchmark, sub_benchmarks=None, iterations=2, discard=0,
                 env=None, custom_iterations_fn=None):
        self._benchmark = benchmark
        self._sub_benchmarks = sub_benchmarks
        if not sub_benchmarks:
            self._sub_benchmarks = []
        self._iterations = iterations
        self._discard = discard
        self._pm = ProjectMap()
        self._env = env
        self._opt = Options()
        if self._env is None:
            self._env = {}
        self._opt.update_env(self._env)
        self._custom_iterations_fn = custom_iterations_fn

    def build(self):
        # todo(majanes) possibly verify that benchmarks are in /opt
        pass

    def test(self):
        iterations = self._iterations
        save_dir = os.getcwd()
        if self._opt.hardware == "builder":
            print "ERROR: hardware must be set to a specific sku.  'builder' is not a valid hardware setting."
            assert(False)
        hw = self._opt.hardware[:3]
        mesa_dir = "/tmp/build_root/" + self._opt.arch + "/" + hw + "/usr/local/lib"
        os.chdir(self._pm.project_source_dir("sixonix"))

        env = self._env
        # set the resolution to 1080p
        (out, _) = run_batch_command(["xrandr"],
                                     streamedOutput=False,
                                     quiet=True,
                                     env=env)
        for line in out.splitlines():
            words = line.split()
            if words[1] != "connected" or words[2] == "secondary":
                continue
            run_batch_command(["xrandr", "--output", words[0], "--mode", "1920x1080"],
                              quiet=True, streamedOutput=False, env=env)
        
        (out, _) = run_batch_command(["xdpyinfo"],
                                     quiet=True,
                                     streamedOutput=False,
                                     env=env)
        for line in out.splitlines():
            if "dimensions:" not in line:
                continue
            if "1920x1080" not in line:
                print "ERROR: could not set screen resolution to 1080p"
                print line
                assert(False)
            # else resolution is correct
            break

        benchmarks = [[self._benchmark.upper()]]
        if self._sub_benchmarks:
            benchmarks = [[self._benchmark.upper(), b] for b in self._sub_benchmarks]
        scores = dict([[b[-1],[]] for b in benchmarks])

        # build a list of each benchmark to run
        bench_runs = []
        iterations = self._iterations
        it_multiplier = 1
        if self._opt.type == "daily":
            it_multiplier = 5
        for b in benchmarks:
            if self._custom_iterations_fn:
                iterations = self._custom_iterations_fn(b[-1], hw) or iterations
            bench_runs += [b] * iterations * it_multiplier

        random.shuffle(bench_runs)
        iteration = 0
        for b in bench_runs:
            cmd = ["./glx.sh", mesa_dir] + b
            print " ".join(cmd)
            (out, err) = run_batch_command(cmd, streamedOutput=False, env=env)
            if err:
                print "err: " + err
            if iteration >= self._discard:
                if not out:
                    print "ERROR: no score: " + b[-1]
                    continue
                scores[b[-1]].append(float(out.splitlines()[-1]))
            iteration += 1

        os.chdir(save_dir)
        for b in benchmarks:
            result = {}
            benchmark = self._benchmark
            if len(b) > 1:
                # for synmark, use the sub-benchmark name
                benchmark = b[1]
            r = str(RevisionSpecification().revision("mesa"))
            scale = 1.0
            try:
                scale = yaml.load(open(self._pm.project_build_dir("sixonix") + "/scale.yml"))[benchmark][hw]
            except:
                print "WARN: failed to find scale for " + benchmark
            result[benchmark] = {hw: {"mesa=" + r: [{"score": scores[b[-1]], "scale": scale}]}}
            out_dir = "/tmp/build_root/" + self._opt.arch + "/scores/" + benchmark + "/" + hw
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            outf = out_dir + "/" + datetime.datetime.now().isoformat() + ".json"
            with open(outf, 'w') as of:
                json.dump(result, fp=of)
                
        Export().export_perf()
        check_gpu_hang(False)

    def clean(self):
        pass


