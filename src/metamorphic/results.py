import csv


def stat_to_str(rule:str, stats: dict) -> str:
    return (f"\n - rule {rule}: " 
            f"{stats['checks']} checks, " 
            f"fail {stats['fail']} times, " 
            f"satisfied {stats['pass']} times. " 
            f"Fail rate = {stats['fail_rate']}")


class Result:

    def __init__(self):
        self.results_dict = dict()

    def add(self, name, results):
        self.results_dict[name] = results

    def __str__(self):
        result = 'Statistics:'
        stats_dict = self.stats()
        for rule in stats_dict:
            result += stat_to_str(rule, stats_dict[rule])
        return result

    def stats(self) -> dict:
        """
        :return: dictionary with stats (checks, pass, fail, not_applicable, fail_rate) about each rule
        """
        stats_dict = dict()
        for rule in self.results_dict:
            total = sum(len(files) for files in self.results_dict[rule].values())
            sat = len(self.results_dict[rule]['pass'])
            fail = len(self.results_dict[rule]['fail'])
            not_applic = len(self.results_dict[rule]['not_applicable'])
            if (sat + fail) > 0:
                fail_rate = 100.0 * fail / (sat + fail)
            else:
                fail_rate = 0.0
            stats_dict[rule] = {
                'checks': total,
                'pass': sat,
                'fail': fail,
                'not_applicable':  not_applic,
                'fail_rate': f"{fail_rate:.2f}%"
            }
        return stats_dict

    def to_csv(self, file_name: str):
        stats_dict = self.stats()
        with open(file_name, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=['rule', 'checks', 'pass', 'fail', 'not_applicable', 'fail_rate'])
            writer.writeheader()
            for key, value in stats_dict.items():
                row = {'rule': key}
                row.update(value)
                writer.writerow(row)


    
    