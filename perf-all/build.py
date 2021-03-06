#!/usr/bin/python

import glob
import json
import git
import os.path as path
import sys
import yaml
import numpy
sys.path.append(path.join(path.dirname(path.abspath(sys.argv[0])), ".."))
import build_support as bs

class MesaStats:
    def __init__(self):
        self.opts = bs.Options()


    def merge_scores(self, all_scores, score):
        for k,v in score.iteritems():
            if k not in all_scores:
                # initialize default
                if isinstance(v, list):
                    all_scores[k] = []
                else:
                    all_scores[k] = {}

            if isinstance(v, list):
                all_scores[k] += v
            else:
                self.merge_scores(all_scores[k], v)

    def test(self):
        # create per-benchmark-per-platform files containing all
        # scores to date

        # at a later point, we may want to combine data sets so
        # developers can see all skylake benchmarks together, for
        # example.

        # canoninical path is
        # /mnt/jenkins/results/perf/mesa={rev}/m64/scores/{benchmark}/{platform}/{date}.json:
        all_scores = {}
        for a_score_file in glob.glob(self.opts.result_path +
                                      "/../*/m64/scores/*/*/*.json"):
            with open(a_score_file, "r") as f:
                a_score = json.load(f)
            self.merge_scores(all_scores, a_score)

        pm =  bs.ProjectMap()
        mesa_repo = git.Repo(pm.project_source_dir("mesa"))
        sixonix_config = yaml.load(open(pm.project_build_dir("sixonix") + "/scale.yml"))

        # add mean score and date to data set
        for benchmark, platform in all_scores.iteritems():
            for platform_name, pscores in platform.iteritems():
                scores_by_date = {}
                for commit, series in pscores.iteritems():
                    accumulated_score = {}
                    normalized_runs = []
                    for run in series:
                        normalized_runs += [ r / run["scale"] for r in run["score"]]
                    if not normalized_runs:
                        continue
                    accumulated_score["score"] = numpy.mean(normalized_runs, dtype=numpy.float64)
                    accumulated_score["deviation"] = numpy.std(normalized_runs, dtype=numpy.float64) / accumulated_score["score"]
                    accumulated_score["commit"] = commit
                    date = mesa_repo.commit(commit.split("=")[1]).committed_date
                    accumulated_score["date"] = date
                    pscores[commit] = accumulated_score
                    scores_by_date[date] = accumulated_score
                dates = scores_by_date.keys()
                dates.sort()
                sixonix_bench = sixonix_config[benchmark]
                platform[platform_name] = {"mesa": [scores_by_date[d] for d in dates]}
                if "UFO" in sixonix_bench and platform_name in sixonix_bench["UFO"]:
                    platform[platform_name]["UFO"] = sixonix_bench["UFO"][platform_name] / sixonix_bench[platform_name]
                
        with open(self.opts.result_path + "/../scores.json", "w") as of:
            json.dump(all_scores, fp=of)

    def build(self):
        pass
    def clean(self):
        pass


bs.build(MesaStats())
