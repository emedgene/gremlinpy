import uuid

class Gremlin(object):
    PARAM_PREFIX = 'GPY_PARAM'
    
    def __init__(self, graph_variable='g'):
        self.gv  = graph_variable
        self.top = GraphVariable(self, graph_variable)
        
        self.reset()

    def reset(self):
        self.parent       = None
        self.bottom       = self.top
        self.bound_params = {}
        self.bound_param  = str(uuid.uuid4())[-5:]
        self.bound_count  = 0
        self.top.next     = None
        
        return self.set_graph_variable(self.gv)

    def __getattr__(self, attr):
        attr = Attribute(self, attr)
        
        return self.add_token(attr)
    
    def __call__(self, *args):
        func = Function(self, str(self.bottom), list(args))
        self.bottom.next = func
        
        return self.remove_token(self.bottom).add_token(func)
            
    def __getitem__(self, val):
        if type(val) is not slice:
            val = slice(val, None, None)
            
        index = Index(self, val)
        
        return self.add_token(index)
        
    def __str__(self):
        return self.__unicode__()
    
    def __unicode__(self):
        token   = self.top
        prev   = token
        tokens = []
        
        while token:
            string = str(token)
            next   = token.next

            if len(tokens) and token.concat and type(next) is not Raw:
                tokens.append(prev.concat)

            tokens.append(string)

            prev = token
            token = token.next
        
        return ''.join(tokens)
        
    def set_parent_gremlin(self, gremlin):
        self.parent = gremlin
        
        return self.bind_params(self.bound_params)
        
    def bind_params(self, params=None):
        if params is None:
            params = []

        for value in params:
            self.bind_param(value)
        
        return self.bound_params
        
    def bind_param(self, value, name=None):
        self.bound_count += 1
        
        if value in self.bound_params:
            name = value
            value = self.bound_params[value]

        if name is None:
            name = '%s_%s_%s' % (self.PARAM_PREFIX, self.bound_param, \
                self.bound_count)

        self.bound_params[name] = value

        if self.parent is not None:
            self.parent.bind_param(value, name)

        return (name, value)
        
    def unbound(self, function, *args):
        unbound = UnboudFunction(self, function, args)
        
        return self.add_token(unbound)

    def close(self, value, *args):
        if args:
            close = ClosureArguments(self, value, args)
        else:
            close = Closure(self, value)
        
        return self.add_token(close)
        
    def raw(self, value):
        raw = Raw(self, value)
        
        return self.add_token(raw)
        
    def add_token(self, token):
        self.bottom.next = token
        self.bottom = token
        
        return self
        
    def remove_token(self, remove):
        token = self.top
        
        while token:
            if token.next == remove:
                token.next = token.next.next
                break
                
            token = token.next
        
        return self
        
    def set_graph_variable(self, graph_variable='g'):
        self.top.value = graph_variable
        
        return self
        
    def apply_statement(self, statement):
        statement.gremlin = self

        return self


class Token(object):
    next = None
    value = None
    args = []
    concat = None
    
    def __init__(self, gremlin, value, args=None):
        self.gremlin = gremlin
        self.value = value

        if args is None:
            args = []

        self.args = args
        
    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return self.value


class GraphVariable(Token):
    concat = '.'
    
    def __unicode__(self):
        if self.value == '':
            self.concat = ''
            
        return self.value


class Attribute(Token):
    concat = '.'


class Function(Token):
    """
    class used to create a Gremlin function
    it assumes that the last argument passed to the function is the only thing 
    that will be bound
    if you need more than the last argument bound, you can do:
        
        g = Gremlin()
        value1 = g.bind_param('value1')[0]
        value2 = g.bind_param('value2')[0]
        g.functionName('not_bound', value1, value2, ...)
    """
    concat = '.'

    def __unicode__(self):
        params = {}

        if len(self.args):
            bound  = self.args.pop()
            params = self.args
            
            if type(bound) is Gremlin:
                bound.set_parent_gremlin(self.gremlin)
                
                params.append(str(bound))
            else:
                params.append(self.gremlin.bind_param(bound)[0])
            
        return '%s(%s)' % (self.value, ', '.join(params))
        
class UnboudFunction(Token):
    concat = '.'
    
    def __unicode__(self):
        return '%s(%s)' % (self.value, ', '.join(self.args))


class Index(Token):
    def __unicode__(self):
        if self.value.stop is not None:
            index = '[%s..%s]' % (self.value.start, self.value.stop)
        else:
            index = '[%s]' % self.value.start
        
        return index


class Closure(Token):
    def __unicode__(self):
        if type(self.value) is Gremlin:
            self.value.set_parent_gremlin(self.gremlin)
            
        return '{%s}' % str(self.value)


class ClosureArguments(Token):
    def __unicode__(self):
        if type(self.value) is Gremlin:
            self.value.set_parent_gremlin(self.gremlin)
            
        return '{%s -> %s}' % (','.join(self.args), str(self.value))


class Raw(Token):
    def __unicode__(self):
        if type(self.value) is Gremlin:
            self.value.set_parent_gremlin(self.gremlin)
        
        return str(self.value)
