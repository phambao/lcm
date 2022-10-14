class SerializerMixin:

    def get_params(self):
        return self.context['request'].__dict__[
            'parser_context']['kwargs']

    def is_param_exist(self, param):
        return param in self.get_params().keys()
