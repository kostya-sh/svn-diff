"""
  Very simple template engine.
  Supports following features:

  - variable substitution using ${var_name[.prop_name]} syntax
    prop_name can be object method without arguments
  - if statement using following syntax (if and endif should be on separate lines)::
    
      #if(expr)
          content goes here
      #endif

  - for loop using following syntax (for and endfor should be on separate lines)::
  
      #for(var in list_var_name)
          content goes here ${var}, ${var_index}
      #endif
"""

import re

EXPR_SUBST_RE = re.compile(r"(\$\{[.\w]+\})")

IF_RE = re.compile(r"#if *\(([.\w]+)\)")
END_IF = "#endif"

FOR_RE = re.compile(r"#for *\((\w+) +in +([.\w]+)\)")
END_FOR = "#endfor"

def eval_expr(expr, context):
    """
    Evaluates expression var_name[.prop_name1[prop_name2[....]]]
    var_name is looked up in dictionary context
    
    >>> print eval_expr("var.prop", {})
    None
    >>> print eval_expr("var", {'var': 'value'})
    value
    >>> print eval_expr("var2", {'var': 'value'})
    None
    >>> print eval_expr("var.upper", {'var': 'value'})
    VALUE
    >>> print eval_expr("var.upper.lower", {'var': 'vAluE'})
    value
    """
    parts = expr.split(".")
    
    value = context.get(parts[0], None)
    i = 1;
    while value is not None and i < len(parts):
        value = getattr(value, parts[i])
        if callable(value):
            value = value()
        i += 1
        
    return value

def render(template, context):
    """
    Render given template using variables from context dictionary
    
    >>> print render('''line 1
    ... line 2''', {})
    line 1
    line 2
    
    >>> print render('Hello ${var}!!!', {'var': 'world'})
    Hello world!!!
    
    >>> print render('''#if (var)
    ... true
    ... #endif''', {'var': True})
    true
    
    >>> print render('''false
    ... #if (var)
    ... true
    ... #endif''', {'var': False})
    false
    
    >>> print render('''#if (var1)
    ...   #if (var2)
    ... double true
    ...   #endif
    ... #endif''', {'var1': True, 'var2': True})
    double true
    
    >>> print render('''#for (var in list)
    ... ${start} ${var}
    ... #endfor
    ... --
    ... #for (var in list)
    ... ${var_index}: ${end} ${var}
    ... #endfor
    ... ''', 
    ... {'list': ('John', 'Mary', 'Peter'), 'start': 'Hello', 'end': 'Bye'})
    Hello John
    Hello Mary
    Hello Peter
    --
    0: Bye John
    1: Bye Mary
    2: Bye Peter
    
    >>> print render('''#for (var in list)
    ... #if (var)
    ... ${var}
    ... #endif
    ... #endfor''', 
    ... {'list': (True, False)})
    True
    
    >>> print render('''#for (var1 in list1)
    ... - ${var1}
    ... #for (var2 in list2)
    ... -- ${var2} ${var1}
    ... #endfor
    ... #endfor''', 
    ... {'list1': ('Apple', 'Pear'), 'list2': ('Green', 'Red')})
    - Apple
    -- Green Apple
    -- Red Apple
    - Pear
    -- Green Pear
    -- Red Pear
    """
    
    result = ""
    
    if_stack = [] # elements are evaluated expressions from context

    for_match = None
    for_sub_template = ""
    for_count = 0
    
    for line in template.splitlines():
        # found endfor - render for_sub_template
        if line.find(END_FOR) >= 0:
            if for_count == 1:
                # parse for expression
                var_name = for_match.group(1)
                collection = eval_expr(for_match.group(2), context)
                
                # render for template every element in collection
                for_context = {}
                for_context.update(context)
                for (index, elem) in enumerate(collection):
                    for_context[var_name] = elem
                    for_context["%s_index" % var_name] = index
                    result += render(for_sub_template, for_context)
                    result += "\n"
                    
                # reset current state
                for_match = None
                for_sub_template = ""
                for_count = 0
            else:
                for_sub_template += "%s\n" % line
                for_count -= 1

            continue
        
        m = FOR_RE.search(line)
        if m is not None:
            for_count += 1

        # collect "for sub template"
        if for_match is not None:
            for_sub_template += "%s\n" % line
            continue
        
        # handle for
        if for_match is None and m is not None:
            for_match = m
            continue
        
        # handle if
        if len(if_stack) > 0 and not if_stack[-1]:
            continue
        m = IF_RE.search(line)
        if m is not None:
            if_stack.append(eval_expr(m.group(1), context))
            continue
        if line.find(END_IF) >= 0:
            if_stack.pop()
            continue
        
        # handle expressions
        for expr in EXPR_SUBST_RE.findall(line):
            line = line.replace(expr, str(eval_expr(expr[2:-1], context)))

        result += line
        result += "\n"
        
    return result.strip()

if __name__ == "__main__":
    import doctest
    doctest.testmod()
