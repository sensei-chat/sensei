import random
import copy
from .utils.exceptions import *
from .utils.utilities import *
import numpy as np
import logging
logger = logging.getLogger('Info Logger')


class VarGenerators:

    def __init__(self, variable_list):

        self.combinations = 0
        self.variable_list = variable_list
        self.generator_list = self.create_generator_list()

    class ForwardMatrixGenerator:
        def __init__(self):
            self.forward_function_list = []
            self.dependence_tuple_list = []  # [(size, toppings), (toppings,drink), (drink, None)]
            self.dependent_list = []
            self.independent_list = []
            self.dependence_matrix = []
            self.dependent_generators = []
            self.independent_generators = []

        def get_matrix(self, dependent_variable_list):
            self.dependence_matrix.clear()
            for index, dependence in enumerate(dependent_variable_list):
                self.dependence_matrix.append([])
                for variable in dependence:
                    for forward in self.forward_function_list:
                        if variable == forward['name']:
                            self.dependence_matrix[index].append(forward['data'])

        def add_forward(self,
                        forward_variable):  # 'name': var_name, 'data': data_list,'function': content['function'],'dependence': dependence}
            self.forward_function_list.append(forward_variable)

            if forward_variable['dependence']:
                master = forward_variable['dependence']
                slave = forward_variable['name']
                self.dependence_tuple_list.append((slave, master))
                for indep_item in self.independent_list:
                    if indep_item == master:
                        self.independent_list.remove(master)
                        self.dependence_tuple_list.append((master, None))

            else:
                if self.dependence_tuple_list:
                    dtlc = self.dependence_tuple_list.copy()
                    for dependence in dtlc:  # [(size, toppings), (toppings,drink), (drink, None)]
                        if forward_variable['name'] in dependence:
                            master = forward_variable['name']
                            self.dependence_tuple_list.append((master, None))
                            break
                    else:
                        master = forward_variable['name']
                        self.independent_list.append(master)
                else:
                    master = forward_variable['name']
                    self.independent_list.append(master)

            if self.dependence_tuple_list:
                self.dependent_list = build_sequence(self.dependence_tuple_list)
                self.get_matrix(self.dependent_list)

        @staticmethod
        def combination_generator(matrix):
            if not matrix:
                while True:
                    yield []
            else:
                lengths = [len(lst) for lst in matrix]
                indices = [0] * len(matrix)
                while True:
                    # Yield the current combination based on indices
                    yield [matrix[i][indices[i]] for i in range(len(matrix))]
                    # Increment indices from the last position
                    i = len(matrix) - 1
                    while i >= 0:
                        indices[i] += 1
                        if indices[i] < lengths[i]:
                            break
                        else:
                            indices[i] = 0
                            i -= 1

        def get_combinations(self):
            if self.dependence_matrix:
                combinations = []
                for matrix in self.dependence_matrix:
                    combinations_one_matrix = 1
                    for sublist in matrix:
                        combinations_one_matrix *= len(sublist)
                    combinations.append(combinations_one_matrix)
                return max(combinations)
            else:
                return 0

        @staticmethod
        def forward_generator(value_list):
            while True:
                for sample in value_list:
                    yield [sample]

        def get_generator_list(self):
            function_map = {function['name']: function['data'] for function in self.forward_function_list}

            independent_generators = [
                {'name': i, 'generator': self.forward_generator(function_map[i])} for i in self.independent_list if
                i in function_map
            ]

            dependent_generators = [
                {'name': val, 'generator': self.combination_generator(self.dependence_matrix[index])} for index, val in
                enumerate(self.dependent_list)
            ]

            return independent_generators + dependent_generators

    def create_generator_list(self):
        generator_list = []
        my_forward = self.ForwardMatrixGenerator()
        for variable in self.variable_list:
            name = variable['name']
            data = variable['data']
            pattern = r'(\w+)\((\w*)\)'
            if not variable['function'] or variable['function'] == 'default()':
                generator = self.default_generator(data)
                generator_list.append({'name': name, 'generator': generator})
            else:
                match = re.search(pattern, variable['function'])
                if match:
                    handler_name = match.group(1)
                    count = match.group(2) if match.group(2) else ''
                    if handler_name == 'random':
                        if count == '':
                            generator = self.random_choice_generator(data)
                            generator_list.append({'name': name, 'generator': generator})
                        elif count.isdigit():
                            count_digit = int(count)
                            generator = self.random_choice_count_generator(data, count_digit)
                            generator_list.append({'name': name, 'generator': generator})
                        elif count == 'rand':
                            generator = self.random_choice_random_count_generator(data)
                            generator_list.append({'name': name, 'generator': generator})

                    elif handler_name == 'forward':
                        my_forward.add_forward(variable)

                    elif handler_name == 'another':
                        generator = self.another_generator(data)
                        generator_list.append({'name': name, 'generator': generator})
                    else:
                        raise InvalidGenerator(f'Invalid generator function: {handler_name}')
                else:
                    raise InvalidFormat(f"an invalid function format was used: {variable['function']}")
        combinations = my_forward.get_combinations()
        self.combinations = combinations
        return generator_list + my_forward.get_generator_list()

    @staticmethod
    def default_generator(data):
        while True:
            yield [data]

    @staticmethod
    def random_choice_generator(data):
        while True:
            yield [random.choice(data)]

    @staticmethod
    def random_choice_count_generator(data, count):
        while True:
            sample = random.sample(data, min(count, len(data)))
            yield sample

    @staticmethod
    def random_choice_random_count_generator(data):
        while True:
            count = random.randint(1, len(data))
            sample = random.sample(data, min(count, len(data)))
            yield sample

    @staticmethod
    def another_generator(data):
        while True:
            copy_list = data[:]
            random.shuffle(copy_list)
            for sample in copy_list:
                yield [sample]


def reorder_variables(entries):
    def parse_entry(entry):

        match = re.search(r'forward\((.*?)\)', entry['function'])
        if match:
            slave = entry['name']
            master = match.group(1)
            return slave, master

    def reorder_list(dependencies):
        tuple_list = []
        none_list = []
        for main_tuple in dependencies:
            if main_tuple:
                for comp_tuple in dependencies:
                    if comp_tuple:
                        if main_tuple[1] == comp_tuple[0]:
                            tuple_list.append(main_tuple)
                            tuple_list.append(comp_tuple)
            else:
                none_list.append(main_tuple)

        tuple_list = list(dict.fromkeys(tuple_list))
        return tuple_list

    dependencies_list = []

    for entry in entries:
        dependencies_list.append(parse_entry(entry))

    reordered_list = reorder_list(dependencies_list)

    editable_entries = entries.copy()
    new_entries = []
    for tupl in reordered_list:
        for entry in entries:
            if tupl[0] == entry['name']:
                new_entries.append(entry)
                editable_entries.remove(entry)
    reordered_entries = new_entries + editable_entries
    return reordered_entries


def dependency_error_check(variable_list):
    for slave in variable_list:
        for master in variable_list:
            if slave['dependence'] == master['name']:
                pattern = r'(\w+)\((\w*)\)'
                match = re.search(pattern, master['function'])
                function = match.group(1)
                if function != 'forward':
                    raise InvalidDependence(f"the following function doesn't admit dependence: {function}()")


def check_circular_dependency(items):
    # Building a name-to-dependency mapping
    dependencies = {}
    for item in items:
        name = item['name']
        dep = item['dependence']
        dependencies[name] = dep

    # Función para realizar DFS y detectar ciclos
    def visit(node, visited, stack):
        if node in stack:
            # Se detectó una dependencia circular
            cycle = ' -> '.join(stack + [node])
            raise Exception(f"Circular dependency detected: {cycle}")
        if node in visited or node not in dependencies:
            return
        stack.append(node)
        dep = dependencies[node]
        if dep is not None:
            visit(dep, visited, stack)
        stack.pop()
        visited.add(node)

    visited = set()
    for node in dependencies.keys():
        if node not in visited:
            visit(node, visited, [])


class AskAboutClass:

    def __init__(self, data):

        self.variable_list = self.get_variables(data)
        self.str_list = self.get_phrases(data)
        self.var_generators, self.combinations = self.variable_generator(self.variable_list)
        self.phrases = self.str_list.copy()
        self.picked_elements = []

    @staticmethod
    def get_variables(data):
        variables = []

        for item in data:
            if isinstance(item, dict):
                var_name = list(item.keys())[0]
                content = item[var_name]
                content_data = content['data'].copy()
                if isinstance(content_data, dict) and 'file' in content_data:  # check for personalized functions
                    path = content_data['file']
                    function = content_data['function_name']
                    if 'args' in content_data:
                        function_arguments = content_data['args']
                        data_list = execute_list_function(path, function, function_arguments)
                    else:
                        data_list = execute_list_function(path, function)
                elif isinstance(content_data, dict) and 'date' in content_data:  # check for date generator
                    data_list = get_date_list(content_data['date'])
                else:
                    if content_data:
                        data_list = content_data
                    else:
                        raise EmptyListExcept(f'Data list is empty.')

                if isinstance(content_data, list):  # check for any() in data list
                    any_list = []
                    item_list = []
                    for index, value in enumerate(data_list):
                        if isinstance(value, str):
                            if 'any(' in value:
                                any_list.append(value)
                            else:
                                item_list.append(value)
                        else:
                            item_list.append(value)

                    if any_list:
                        data_list = get_any_items(any_list, item_list)
                    else:
                        data_list = item_list

                if content['type'] == 'string':
                    for i in data_list:
                        if type(i) is not str:
                            raise InvalidDataType(f'The following item is not a string: {i}')
                    if data_list:
                        output_data_list = data_list
                    else:
                        raise EmptyListExcept(f'Data list is empty.')

                elif content['type'] == 'int':
                    if isinstance(data_list, list):
                        for i in data_list:
                            if type(i) is not int:
                                raise InvalidDataType(f'The following item is not an integer: {i}')
                        if data_list:
                            output_data_list = data_list
                        else:
                            raise EmptyListExcept(f'Data list is empty.')
                    elif isinstance(data_list, dict) and 'min' in data_list:
                        keys = list(data_list.keys())
                        data = data_list
                        if 'step' in keys:
                            if isinstance(data['min'], int) and isinstance(data['max'], int) and isinstance(
                                    data['step'], int):
                                output_data_list = np.arange(data['min'], data['max'], data['step'])
                                output_data_list = output_data_list.tolist()
                                output_data_list.append(data['max'])

                            else:
                                raise InvalidDataType(f'Some of the range function parameters are not integers.')
                        else:
                            if isinstance(data['min'], int) and isinstance(data['max'], int):
                                output_data_list = np.arange(data['min'], data['max'])
                                output_data_list = output_data_list.tolist()
                            else:
                                raise InvalidDataType(f'Some of the range function parameters are not integers.')
                    else:
                        raise InvalidFormat(f'Data follows an invalid format.')

                elif content['type'] == 'float':
                    if isinstance(data_list, list):
                        for i in data_list:
                            if not isinstance(i, (int, float)):
                                raise InvalidDataType(f'The following item is not a number: {i}')
                        if data_list:
                            output_data_list = data_list
                        else:
                            raise EmptyListExcept(f'Data list is empty.')
                    elif isinstance(data_list, dict) and 'min' in data_list:
                        keys = list(data_list.keys())
                        data = content['data']
                        if 'step' in keys:
                            output_data_list = np.arange(data['min'], data['max'], data['step'])
                            output_data_list = output_data_list.tolist()
                            output_data_list.append(data['max'])

                        elif 'linspace' in keys:
                            output_data_list = np.linspace(data['min'], data['max'], data['linspace'])
                            output_data_list = output_data_list.tolist()
                        else:
                            raise MissingStepDefinition(
                                f'"step" or "lisnpace" parameter missing. A step separation must be defined.')
                    else:
                        raise InvalidFormat(f'Data follows an invalid format.')
                else:
                    raise InvalidItemType(f'Invalid data type for variable list.')

                pattern = r'(\w+)\((\w*)\)'
                if not content['function']:
                    content['function'] = 'default()'

                match = re.search(pattern, content['function'])
                if match:
                    count = match.group(2) if match.group(2) else ''
                    if not count == '' or count == 'rand' or count.isdigit():
                        dependence = count
                    else:
                        dependence = None
                else:
                    dependence = None

                logger.info(f"{var_name}: {output_data_list}")

                dictionary = {'name': var_name, 'data': output_data_list,
                              'function': content['function'],
                              'dependence': dependence}  # (size, [small, medium], random(), toppings)
                variables.append(dictionary)
        reordered_variables = reorder_variables(variables)
        dependency_error_check(reordered_variables)
        check_circular_dependency(reordered_variables)
        return reordered_variables

    @staticmethod
    def get_phrases(data):
        str_content = []
        for item in data:
            if isinstance(item, str):
                str_content.append(item)
        return str_content

    @staticmethod
    def variable_generator(variables):
        generators = VarGenerators(variables)
        generators_list = generators.generator_list
        combinations = generators.combinations
        return generators_list, combinations

    def picked_element_already_in_list(self, match, value):
        element_list = [list(element.keys())[0] for element in self.picked_elements]
        if match.group(1) not in element_list:
            self.picked_elements.append({match.group(1): value})

    def replace_variables(self, generator):
        pattern = re.compile(r'\{\{(.*?)\}\}')
        if isinstance(generator['name'], list) and len(generator['name']) > 1:  # this is for nested forwards

            values = next(generator['generator'])
            keys = generator['name']
            mapped_combinations = dict(zip(keys, values))
            self.picked_elements.extend([{key: value} for key, value in mapped_combinations.items()])
            replaced_phrases = []
            for phrase in self.phrases.copy():
                def replace_variable(match):
                    variable = match.group(1)
                    return mapped_combinations.get(variable, match.group(0))

                replaced_phrase = re.sub(r'\{\{(\w+)\}\}', str(replace_variable), phrase)
                replaced_phrases.append(replaced_phrase)
            self.phrases = replaced_phrases

        else:  # this is for everything else
            value = next(generator['generator'])
            name = generator['name']

            for index, text in enumerate(self.phrases):
                matches = re.finditer(pattern, text)
                for match in matches:
                    if match.group(1) == name:
                        self.picked_element_already_in_list(match, value)
                        # self.picked_elements.append({match.group(1): value})
                        replacement = ', '.join([str(v) for v in value])
                        text = text.replace(match.group(0), replacement)
                        self.phrases[index] = text
                        break
                else:
                    self.phrases[index] = text




    def ask_about_processor(self):
        for generator in self.var_generators:
            self.replace_variables(generator)
        return self.phrases

    def prompt(self):
        phrases = self.ask_about_processor()
        return list_to_phrase(phrases, True)

    def reset(self):
        self.picked_elements = []
        self.phrases = self.str_list.copy()
