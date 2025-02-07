from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Any
from types import SimpleNamespace

from . import get_filtered_tests, empty_filtered_tests
from .rule_utils import *

# Do not remove this import, it is used to dynamically import the functions
from .rule_utils import filtered_tests, _conversation_length, extract_float, _only_talks_about
from .rule_utils import _utterance_index, _chatbot_returns, _repeated_answers, _data_collected, _missing_slots, _responds_in_same_language
from .rule_utils import _responds_in_same_language, semantic_content

from metamorphic.tests import Test


class Rule(BaseModel):
    name: str
    description: str
    conversations: int = 1
    active: Optional[bool] = True
    when: Optional[str] = "True"
    if_: Optional[str] = Field("True", alias="if")
    then: str
    yields: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def check_aliases(cls, values: Any) -> Any:
        if 'oracle' in values:      # Handle 'oracle' or 'then' interchangeably
            values['then'] = values.pop('oracle')
        if 'conversations' in values and values['conversations'] == 'all':  # handle global rules ('all')
            values['conversations'] = -1
        return values

    def test(self, tests: List[Test], verbose: bool = False) -> dict:
        print(f" - Checking rule {self.name} [conversations: {self.conversations if self.conversations!=-1 else 'all'}]")
        if self.conversations == 1:
            return self.__property_test(tests, verbose)
        elif self.conversations == -1: # global rules
            return self.__global_test(tests, verbose)
        else: # by now we assume just 2 conversations...
            return self.__metamorphic_test(tests, verbose)

    def __global_test(self, tests: List[Test], verbose: bool) -> dict:
        results = {'pass': [], 'fail': [], 'not_applicable': []}
        # filter the conversations, to select only those satisfying when and if
        empty_filtered_tests()
        filtered = get_filtered_tests()
        for test in tests:
            test_dict = test.to_dict()
            conv = [SimpleNamespace(**test_dict)]
            test_dict['conv'] = conv
            test_dict.update(util_functions_to_dict())
            if self.applies(test_dict) and self.if_eval(test_dict):
                filtered.append(test)
            else: # does not apply
                results['not_applicable'].append(test.file_name)
                if verbose:
                    print(f"   - On file {test.file_name}")
                    print(f"     -> Does not apply.")

        try:
            if self.then_eval(test_dict):
                results['pass'].append(filtered)
                if verbose:
                    print(f"   - On files {', '.join([test.file_name for test in filtered])}")
                    print(f"     -> Satisfied!")
            else:
                results['fail'].append(filtered)
        except Exception:
            results['not_applicable'].append(filtered)
            if verbose:
                print(f"   - On files {', '.join([test.file_name for test in filtered])}")
                print(f"     -> Satisfied!")

        return results

    def __property_test(self, tests: List[Test], verbose: bool) -> dict:
        results = {'pass': [], 'fail': [], 'not_applicable': []}
        for test in tests:
            test_dict = test.to_dict()
            conv = [SimpleNamespace(**test_dict)]
            test_dict['conv'] = conv
            test_dict.update(util_functions_to_dict())
            if verbose:
                print(f"   - On file {test.file_name}")
            if self.applies(test_dict):
                if self.if_eval(test_dict):
                    try:
                        return_value = self.then_eval(test_dict)
                    except Exception:
                        self.__handle_not_applicable(verbose, results, test)
                        continue
                    if return_value == True:  # can be a boolean or another value to signal an error
                        self.__handle_pass(verbose, results, test)
                    else:
                        self.__handle_fail(verbose, results, return_value, test_dict, test)
                else:
                    self.__handle_not_applicable(verbose, results, test)
            else:
                self.__handle_not_applicable(verbose, results, test)
        return results


    def __handle_not_applicable(self, verbose, results, *tests):
        if len(tests)==1:
            results['not_applicable'].append(tests[0].file_name)
        else:
            results['not_applicable'].append(tuple(test.file_name for test in tests))
        if verbose: print(f"     -> Does not apply.")

    def __handle_pass(self, verbose, results, *tests):
        if len(tests)==1:
            results['pass'].append(tests[0].file_name)
        else:
            results['pass'].append(tuple(test.file_name for test in tests))
        if verbose:
            print(f"     -> Satisfied!")

    def __handle_fail(self, verbose, results, return_value, test_dict, *tests):
        if len(tests)==1:
            results['fail'].append(tests[0].file_name)
        else:
            results['fail'].append(tuple(test.file_name for test in tests))
        if verbose:
            message = ""
            if self.yields is not None:
                message = ". "+self.yield_eval(test_dict)
            if return_value != False:   # return_value can be a boolean or something else
                print(f"     -> NOT Satisfied!. Reason: {return_value}{message}.")
            else:
                print(f"     -> NOT Satisfied!. Reason: oracle violated{message}.")

    def __metamorphic_test(self, tests: List[Test], verbose: bool) -> dict:
        results = {'pass': [], 'fail': [], 'not_applicable': []}
        for test1 in tests:
            test_dict1 = test1.to_dict()
            sns = SimpleNamespace(**test_dict1)
            conv = [sns, sns]
            test_dict = {'conv': conv, 'interaction': []}   # just add a dummy interaction variable
            test_dict.update(util_functions_to_dict())
            for test2 in tests:
                if test1 == test2:
                    continue
                test_dict2 = test2.to_dict()
                conv[1] = SimpleNamespace(**test_dict2)
                if verbose:
                    print(f"   - On files: {test1.file_name}, {test2.file_name}")
                if self.applies(test_dict):
                    if self.if_eval(test_dict):
                        try:
                            return_value = self.then_eval(test_dict)
                        except Exception:
                            self.__handle_fail(verbose, results, return_value, test_dict, test1, test2)
                            continue
                        if return_value == True:
                            self.__handle_pass(verbose, results, test1, test2)
                        else:
                            self.__handle_fail(verbose, results, return_value, test_dict, test1, test2)
                    else:
                        self.__handle_not_applicable(verbose, results, test1, test2)
                else:
                    self.__handle_not_applicable(verbose, results, test1, test2)
        return results

    def applies(self, test_dict: dict):
        try:
            return eval(self.when, test_dict)
        except Exception:
            return False

    def if_eval(self, test_dict: dict):
        try:
            return eval(self.if_, test_dict)
        except Exception:
            return False

    def then_eval(self, test_dict: dict):
        code = f"""        
def _eval(**kwargs):
    # unpack parameters
    interaction = kwargs['interaction']
    conv = kwargs['conv']
{self.__unpack_dict(test_dict)}
    
    #wrappers for functions with implicit parameters
{self.__wrapper_functions()}
            
    return {self.then}
        """
        local_namespace = {}
        exec(code, globals(), local_namespace)
        self._eval = local_namespace['_eval']
        return self._eval(**test_dict)
        #return eval(self.then, test_dict)

    def yield_eval(self, test_dict: dict):
        code = f"""        
def _eval(**kwargs):
    # unpack parameters
    interaction = kwargs['interaction']
    conv = kwargs['conv']
{self.__unpack_dict(test_dict)}

    #wrappers for functions with implicit parameters
{self.__wrapper_functions()}

    return {self.yields}
            """
        local_namespace = {}

        exec(code, globals(), local_namespace)
        self._eval = local_namespace['_eval']
        try:
            return str(self._eval(**test_dict))
        except Exception:
            return ""

    def __wrapper_functions(self):
        result = "\n".join(func for func in util_to_wrapper_dict().values())
        return result

    def __unpack_dict(self, dict):
        reserved = ['conv', 'interaction', '__builtins__']
        reserved += util_functions_to_dict().keys()
        code = ""
        for key, value in dict.items():
            if key in reserved:
                continue
            code += "    " + key + f"= kwargs['{key}']\n"
        return code