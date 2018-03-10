import numpy
import random
import time
import pika
from scoop import logger
import abc

class GeneticAlgorithm(metaclass=abc.ABCMeta):
    def __init__(self, population_size, chromosome_size, number_of_generations, server_ip_addr):
        self._population_size = population_size
        self._chromosome_size = chromosome_size
        self._number_of_generations = number_of_generations
        self._server_ip_addr = server_ip_addr

    def initialize_population(self):
        """
        Generate the population
        :return: population
        """
        population = []
        for i in range(0, self._population_size):
            population.append(self._gen_individual())
        return population

    def _gen_individual(self):
        """
        Generate binary array
        :return: individual's chromosome
        """
        return list(map(bytes,
                        numpy.random.randint(
                            2,
                            size=self._chromosome_size)))

    def _crossover(self, father, mother):
        """
        Exchange the random number of bits
        between father and mother
        :param father
        :param mother
        """
        cross = random.randint(0, self._chromosome_size - 1)
        for i in range(0, cross):
            mother[i] = father[i]
        for i in range(cross, self._chromosome_size):
            father[i] = mother[i]

    def _mutation(self, chromosome):
        """
        Invert one random bit based on probability
        :param chromosome
        """
        if numpy.random.choice([True, False], p=[0.1, 0.9]):
            rnd = random.randint(0, self._chromosome_size - 1)
            chromosome[rnd] = abs(chromosome[rnd] - 1)

    def _find_solution(self, population):
        """
        Find the best solution
        :param population
        :return: best_weight, chromosome
        """
        max_val = 0
        max_index = None
        for i in range(0, self._population_size):
            curr_fit = self.fitness(population[i])
            if curr_fit > max_val:
                max_val = curr_fit
                max_index = i
        return max_val, population[max_index]

    @abc.abstractmethod
    def fitness(self, chromosome):
        pass

    @abc.abstractmethod
    def _start_MPI(self):
        pass

    @abc.abstractmethod
    def _process(self,  *positional_parameters, **keyword_parameters):
        pass

    @abc.abstractmethod
    def _send_data(self, data):
        pass

    @abc.abstractmethod
    def _collect_data(self):
        pass

    @abc.abstractmethod
    def _finish_processing(self, received_data, data):
        pass

    @abc.abstractmethod
    def _stop_MPI(self):
        pass

    def process(self, *positional_parameters, **keyword_parameters):
        toReturn = []
        self._start_MPI()
        for i in range(0, self._number_of_generations):
            data = self._process(positional_parameters, keyword_parameters)
            self._send_data(data)
            received_data = self._collect_data()
            toReturn = self._finish_processing(received_data, data)
        return toReturn

