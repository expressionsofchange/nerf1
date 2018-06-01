from time import time
import json

FRAMESIZE = 1 / 30


class Recorder(object):

    def __init__(self):
        self.t0 = time()
        self.f = open('recording.json', 'w')

    def recorder(self, object_name):

        def record(method_name, data):
            full_record = {
                'object_name': object_name,
                'method_name': method_name,
                'time': time() - self.t0,
                'data': data,
            }
            self.f.write(json.dumps(full_record) + '\n')
            self.f.flush()

        return record


class Player(object):

    def __init__(self):
        with open('recording.json') as f:
            self.facts = [json.loads(line.strip()) for line in f.readlines()]

        self.last_t = 0
        self.last_mouse = (0, 0)

    def simulate_tree_input(self, tree, current_t):
        relevant_facts = [fact for fact in self.facts if
                          (self.last_t < fact['time'] <= current_t) and (fact['object_name'] == 'tree')]

        for fact in sorted(relevant_facts, key=lambda d: d['time']):
            if fact['method_name'] == 'generalized_key_press':
                tree._actual_generalized_key_press(fact['data'])  # a single string

            elif fact['method_name'] == 'on_touch_down':
                tree._actual_on_touch_down(Point(**fact['data']))  # duck-type for Point

        self.last_t = current_t

    def get_cursor_position(self, current_t):
        relevant_facts = [fact for fact in self.facts if
                          (self.last_t < fact['time'] <= current_t) and (fact['object_name'] == 'mouse')]

        if len(relevant_facts) > 0:
            fact = min(sorted(relevant_facts, key=lambda d: d['time']))
            self.last_mouse = (fact['data']['x'], fact['data']['y'])

        return self.last_mouse

    def get_click_recentness(self, current_t):
        relevant_facts = [fact for fact in self.facts if
                          (fact['time'] <= current_t) and
                          (fact['object_name'] == 'tree') and
                          (fact['method_name'] == 'on_touch_down')]

        if len(relevant_facts) == 0:
            return 99999

        return current_t - list(sorted(relevant_facts, key=lambda d: d['time']))[-1]['time']


class Point(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y
