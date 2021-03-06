import Orange
import random

data = Orange.data.Table("housing")
test = Orange.data.Table(random.sample(data, 5))
train = Orange.data.Table([d for d in data if d not in test])

lin = Orange.regression.linear.LinearRegressionLearner(train)
lin.name = "lin"
rf = Orange.ensemble.forest.RandomForestLearner(train)
rf.name = "rf"
tree = Orange.regression.tree.TreeLearner(train)
tree.name = "tree"

models = [lin, rf, tree]

print "y    " + " ".join("%-4s" % l.name for l in models)
for d in test[:3]:
    print "%.1f" % (d.get_class()),
    print " ".join("%4.1f" % model(d) for model in models)
