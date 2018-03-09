import numpy as np
import random
import json
import pika
import time
import math
from scoop import logger, futures
NUMBER_OF_GENERATIONS = 100
POPULATION_SIZE = 10
CHROMOSOME_SIZE = 4
KNAPSACK_SIZE = 30
NUM_OF_NEIGHBOURS = 3


class Collect(object):
    def __init__(self):
        self._objects = []

    @property
    def objects(self):
        return self._objects

    def append_object(self, obj):
        return self._objects.append(obj)

    def sort_objects(self):
        return sorted(self._objects, key=lambda x: x.fit, reverse=True)

    def size_of_col(self):
        return len(self._objects)


class Snt(object):
    def __init__(self, fit, chromosome):
        self._fit = fit
        self._chromosome = chromosome

    @property
    def fit(self):
        return self._fit

    @property
    def chromosome(self):
        return self._chromosome

    def __str__(self):
        return "Fitness is " + str(self._fit) + " chromosome is " + str(self.chromosome)

    def __repr__(self):
        return self.__str__()


class Item(object):
    def __init__(self, volume, weight, name):
        self._weight = weight
        self._volume = volume
        self._name = name

    @property
    def volume(self):
        return self._volume

    @property
    def weight(self):
        return self._weight

    @property
    def name(self):
        return self._name


items = {0: Item(10, 30, 'knife'),
         1: Item(20, 40, 'food'),
         2: Item(5, 5, 'rope'),
         3: Item(10, 15, 'matches')}


def initialize_population():
    """
    Generate the population
    :return: population
    """
    population = []
    for i in range(0, POPULATION_SIZE):
        population.append(gen_individual())
    return population


def gen_individual():
    """
    Generate binary array
    :return: individual's chromosome
    """
    return np.random.randint(2, size=CHROMOSOME_SIZE)


def crossover(father, mother):
    """
    Exchange the random number of bits
    between father and mother
    :param father
    :param mother
    """
    cross = random.randint(0, CHROMOSOME_SIZE - 1)
    for i in range(0, cross):
        mother[i] = father[i]
    for i in range(cross, CHROMOSOME_SIZE):
        father[i] = mother[i]


def mutation(chromosome):
    """
    Invert one random bit based on probability
    :param chromosome
    """
    if np.random.choice([True, False], p=[0.1, 0.9]):
        rnd = random.randint(0, CHROMOSOME_SIZE - 1)
        chromosome[rnd] = abs(chromosome[rnd] - 1)


def fitness(chromosome):
    first_sum = 0.0
    second_sum = 0.0
    for c in chromosome:
        first_sum += c**2.0
        second_sum += math.cos(2.0*math.pi*c)
    n = float(len(chromosome))
    return 10-(-20.0*math.exp(-0.2*math.sqrt(first_sum/n)) - math.exp(second_sum/n) + 20 + math.e)


def find_solution(population):
    """
    Find the best solution
    :param population
    :return: best_weight, chromosome
    """
    max_val = 0
    max_index = None
    for i in range(0, POPULATION_SIZE):
        curr_fit = fitness(population[i])
        if curr_fit > max_val:
            max_val = curr_fit
            max_index = i
    return max_val, population[max_index]


def process(chromosome, channels):
    queue_to_produce = str(channels.pop(0))
    queues_to_consume = list(map(str, channels))
    logger.info("starting processing to queue: " + queue_to_produce
                + " and consuming from: " + str(queues_to_consume) + " with chromosome: "
                + str(chromosome))
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='127.0.0.1',
                                  credentials=pika.PlainCredentials("genetic1", "genetic1")))

    channel = connection.channel()

    channel.exchange_declare(exchange='direct_logs',
                             exchange_type='direct')
    channel.basic_qos(prefetch_count=len(queues_to_consume))

    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue

    for queue in queues_to_consume:
        channel.queue_bind(exchange='direct_logs',
                           queue=queue_name,
                           routing_key=queue)
    time.sleep(5)

    for i in range(0, NUMBER_OF_GENERATIONS):
        fit = fitness(chromosome)
        to_send = [float(fit)]
        to_send.extend(list(map(float, chromosome)))
        channel.basic_publish(exchange='direct_logs',
                              routing_key=queue_to_produce,
                              body=json.dumps(to_send))
        logger.info(' [*] Waiting for logs')
        neighbours = Collect()
        while neighbours.size_of_col() != NUM_OF_NEIGHBOURS:
            method_frame, header_frame, body = channel.basic_get(queue=str(queue_name), no_ack=False)
            if body:
                received = list(map(float, json.loads(body)))
                logger.info(queue_to_produce + " RECEIVED " + str(received))

                fit_val = received.pop(0)
                vector = list(map(int, received))
                print("PARSED " + str(fit_val) + " " + str(vector))
                neighbours.append_object(Snt(fit_val, vector))
                channel.basic_ack(method_frame.delivery_tag)

            else:
                logger.info(queue_to_produce + ' No message returned')

        sorted_x = neighbours.sort_objects()
        print("SORTED " + str(sorted_x))
        mother = sorted_x.pop(0).chromosome
        logger.info("father " + str(chromosome) + " mother " + str(mother))
        crossover(chromosome, mother)
        # mutate
        mutation(chromosome)

    fit = fitness(chromosome)
    logger.info("RETURN chromosome " + str(chromosome) + " with fitness " + str(fit))
    connection.close()
    return fit, list(map(float, chromosome))


def initialize_topology(quantity, radius):
    channels_to_return = []
    for x in range(quantity):
        channels = [x]
        for z in range(1, radius + 1):
            if x+z > quantity - 1:
                channels.append(abs(quantity-(x+z)))
            else:
                channels.append(x+z)
            if x-z < 0:
                channels.append(abs((x-z) + quantity))
            else:
                channels.append(x-z)
        channels_to_return.append(channels)
    return channels_to_return


if __name__ == '__main__':
    arr = initialize_topology(POPULATION_SIZE, NUM_OF_NEIGHBOURS)
    popula = initialize_population()
    result = list(futures.map(process, popula, arr))
    dct = {}
    while len(result):
        fitness_val, vector = result.pop(0)
        dct[fitness_val] = vector
    logger.info("END RESULTTTTTT " + str(sorted(dct.items()).pop()))
