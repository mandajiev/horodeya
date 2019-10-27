from django import template

register = template.Library()

@register.tag
def active(parser, token):
    args = token.split_contents()
    template_tag = args[0]
    if len(args) < 2:
        raise template.TemplateSyntaxError("%r tag requires at least one argument" % template_tag)
    return NavSelectedNode(args[1:])

class NavSelectedNode(template.Node):
    def __init__(self, patterns):
        self.patterns = patterns

    def render(self, context):
        path = context['request'].path
        if path == '/':
            path = 'начало'

        for p in self.patterns:
            if p in path:
                return "active" # change this if needed for other bootstrap version (compatible with 3.2)
        return ""
