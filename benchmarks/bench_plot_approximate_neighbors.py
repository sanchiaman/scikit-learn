"""
Benchmark for approximate nearest neighbor search using
locality sensitive hashing forest.

There are two types of benchmarks.

First, accuracy of LSHForest queries are measured for various
hyper-parameters and index sizes.

Second, speed up of LSHForest queries compared to brute force
method in exact nearest neighbors is measures for the
aforementioned settings. In general, speed up is increasing as
the index size grows.
"""

import numpy as np
from tempfile import gettempdir
from time import time

from sklearn.neighbors import NearestNeighbors
from sklearn.neighbors.approximate import LSHForest
from sklearn.datasets import make_blobs
from sklearn.externals.joblib import Memory

m = Memory(cachedir=gettempdir())


@m.cache()
def make_data(n_samples, n_features, n_queries, seed=0):
    """Create index and query data."""
    print('Generating random blob-ish data')
    X, _ = make_blobs(n_samples=n_samples + n_queries,
                      n_features=n_features, centers=100,
                      shuffle=True, random_state=seed)

    # Keep the last samples as held out query vectors: note since we used
    # shuffle=True we have ensured that index and query vectors are
    # samples from the same distribution (a mixture of 100 gaussians in this
    # case)
    return X[:n_samples], X[n_samples:]


def calc_exact_neighbors(X, queries, n_queries, n_neighbors):
    """Measures average times for exact neighbor queries."""
    print ('Building NearestNeighbors for %d samples in %d dimensions' %
           (X.shape[0], X.shape[1]))
    nbrs = NearestNeighbors(algorithm='brute', metric='cosine').fit(X)
    neighbors_list = []
    average_time = 0

    for query in queries:
        t0 = time()
        neighbors = nbrs.kneighbors(query, n_neighbors=n_neighbors,
                                    return_distance=False)
        average_time += time() - t0
        neighbors_list.append(neighbors)
    average_time /= float(n_queries)

    return neighbors_list, average_time


def calc_accuracy(X, queries, n_queries, n_neighbors, exact_neighbors,
                  average_time_exact, **lshf_params):
    """Calculates accuracy and the speed up of LSHForest."""
    print('Building LSHForest for %d samples in %d dimensions' %
          (X.shape[0], X.shape[1]))
    lshf = LSHForest(**lshf_params)
    t0 = time()
    lshf.fit(X)
    lshf_build_time = time() - t0
    print('Done in %0.3fs' % lshf_build_time)

    average_time_approx = 0
    accuracy = 0

    for i, query in enumerate(queries):
        t0 = time()
        approx_neighbors = lshf.kneighbors(query, n_neighbors=n_neighbors,
                                           return_distance=False)
        average_time_approx += time() - t0
        accuracy += np.in1d(approx_neighbors, exact_neighbors[i]).mean()

    average_time_approx /= float(n_queries)
    accuracy /= float(n_queries)
    speed_up = average_time_exact / average_time_approx

    print('Average time for lshf neighbor queries: %0.3fs' %
          average_time_approx)
    print ('Average time for exact neighbor queries: %0.3fs' %
           average_time_exact)
    print ('Average Accuracy : %0.2f' % accuracy)
    print ('Speed up: %0.1fx' % speed_up)

    return speed_up, accuracy


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    # Initialize index sizes
    n_samples = [int(1e3), int(1e4), int(1e5), int(1e6)]
    n_features = int(1e2)
    n_queries = 100
    n_neighbors = 10

    X_index, X_query = make_data(np.max(n_samples), n_features, n_queries,
                                 seed=0)

    params_list = [{'n_estimators': 3, 'n_candidates': 50},
                   {'n_estimators': 5, 'n_candidates': 70},
                   {'n_estimators': 10, 'n_candidates': 100}]

    accuracies = np.zeros((len(n_samples), len(params_list)), dtype=float)
    speed_ups = np.zeros((len(n_samples), len(params_list)), dtype=float)

    for i, sample_size in enumerate(n_samples):
        print ('==========================================================')
        print ('Sample size: %i' % sample_size)
        print ('------------------------')
        exact_neighbors, average_time_exact = calc_exact_neighbors(
            X_index[:sample_size], X_query, n_queries, n_neighbors)
        for j, params in enumerate(params_list):
            print ('LSHF parameters: n_estimators = %i, n_candidates = %i' %
                   (params['n_estimators'], params['n_candidates']))
            speed_ups[i, j], accuracies[i, j] = calc_accuracy(
                X_index[:sample_size], X_query, n_queries, n_neighbors,
                exact_neighbors, average_time_exact, **params)
            print ('')
        print ('==========================================================')

    # Set labels for LSHForest parameters
    colors = ['c', 'm', 'y']
    p1 = plt.Rectangle((0, 0), 0.1, 0.1, fc=colors[0])
    p2 = plt.Rectangle((0, 0), 0.1, 0.1, fc=colors[1])
    p3 = plt.Rectangle((0, 0), 0.1, 0.1, fc=colors[2])

    labels = ['n_estimators=' + str(params_list[0]['n_estimators']) +
              ', n_candidates=' + str(params_list[0]['n_candidates']),
              'n_estimators=' + str(params_list[1]['n_estimators']) +
              ', n_candidates=' + str(params_list[1]['n_candidates']),
              'n_estimators=' + str(params_list[2]['n_estimators']) +
              ', n_candidates=' + str(params_list[2]['n_candidates'])]

    # Plot precision
    plt.figure()
    plt.legend((p1, p2, p3), (labels[0], labels[1], labels[2]),
               loc='upper left')

    for i in range(len(params_list)):
        plt.scatter(n_samples, accuracies[:, i], c=colors[i])
        plt.plot(n_samples, accuracies[:, i], c=colors[i])
    plt.ylim([0, 1.3])
    plt.xlim(np.min(n_samples), np.max(n_samples))
    plt.semilogx()
    plt.ylabel("Precision@10")
    plt.xlabel("Index size")
    plt.grid(which='both')
    plt.title("Precision of first 10 neighbors with index size")

    # Plot speed up
    plt.figure()
    plt.legend((p1, p2, p3), (labels[0], labels[1], labels[2]),
               loc='upper left')

    for i in range(len(params_list)):
        plt.scatter(n_samples, speed_ups[:, i], c=colors[i])
        plt.plot(n_samples, speed_ups[:, i], c=colors[i])
    plt.ylim(0, np.max(speed_ups))
    plt.xlim(np.min(n_samples), np.max(n_samples))
    plt.semilogx()
    plt.ylabel("Speed up")
    plt.xlabel("Index size")
    plt.grid(which='both')
    plt.title("Relationship between Speed up and index size")

    plt.show()
