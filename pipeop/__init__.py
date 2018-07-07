"""
    Class decorator code based on
    https://www.codementor.io/sheena/advanced-use-python-decorators-class-function-du107nxsv
"""

from ast import Call, parse, Name, NodeTransformer, LShift, RShift, \
    increment_lineno
from inspect import getsource, isclass, stack
from textwrap import dedent





class _PipeTransformer(NodeTransformer):

    def visit_BinOp(self, node):
        if isinstance(node.op, (LShift, RShift)):
            # Convert function name / lambda etc without braces into call
            if not isinstance(node.right, Call):
                return self.visit(Call(
                    func=node.right,
                    args=[node.left],
                    keywords=[],
                    starargs=None,
                    kwargs=None,
                    lineno=node.right.lineno,
                    col_offset=node.right.col_offset
                ))
            else:
                # Rewrite a >> b(...) as b(a, ...)
                node.right.args.insert(
                    0 if isinstance(node.op, RShift) else len(node.right.args),
                    node.left)
                return self.visit(node.right)

        else:
            return node


def pipes(func_or_cache_flag=True):

    def pipes_decorator(func_or_class):
        if isclass(func_or_class):
            decorated_name = '__pipes_class_{}'.format(
                func_or_class.__name__)

            first_line_number = 1  # TODO Can we introspect correct number?
            ctx = stack()[2][0].f_locals

        else:
            decorated_name = '__pipes_{}'.format(
                func_or_class.__code__.co_name)
            first_line_number = func_or_class.__code__.co_firstlineno
            ctx = func_or_class.__globals__

        # We only modify the function once
        if not func_or_cache_flag or decorated_name not in ctx:
            # AST data structure representing parsed function code
            tree = parse(dedent(getsource(func_or_class)))

            # Fix line numbers so that debuggers still work
            increment_lineno(tree, first_line_number - 1)

            # Update name of function to compile
            tree.body[0].name = decorated_name

            # remove the pipe decorator so that we don't recursively
            # call it again. The AST node for the decorator will be a
            # Call if it had braces, and a Name if it had no braces.
            # The location of the decorator function name in these
            # nodes is slightly different.
            tree.body[0].decorator_list = \
                [d for d in tree.body[0].decorator_list
                 if isinstance(d, Call) and d.func.id != 'pipes'
                 or isinstance(d, Name) and d.id != 'pipes']

            # Apply the visit_BinOp transformation
            tree = _PipeTransformer().visit(tree)

            # now compile the AST into an altered function definition
            code = compile(
                tree,
                filename=__file__,
                mode="exec")

            # and execute the definition in the original context
            exec(code, ctx)

        # return the modified function - original is never called
        return ctx[decorated_name]

    if callable(func_or_cache_flag):
        # No arguments passed to @pipes so we received the function to wrap
        # Pass function to the decorator to check for recompile and return
        # modified function
        return pipes_decorator(func_or_cache_flag)

    else:
        # Cache argument was passed to @pipes, so return decorator function
        # reference. The function was defined in a closure with func_or_cache
        # flag being used as a cache flag set to True or False, so it can
        # access the flag and still be passed the function when it is called.
        return pipes_decorator
