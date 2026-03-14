from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    request = context['request']
    query_params = request.GET.copy()

    for key, value in kwargs.items():
        if value in (None, ''):
            query_params.pop(key, None)
        else:
            query_params[key] = value

    encoded = query_params.urlencode()
    if encoded:
        return f'?{encoded}'
    return ''
