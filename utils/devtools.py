import traceback


def stacktrace(depth=6):
    # exc_type, exc_value, exc_traceback = sys.exc_info()

    stack = traceback.format_exc().splitlines()
    print()

    for n, x in enumerate(stack[1:-1]):
        if n < depth:
            print(x)

    if len(stack) > depth:
        print('  ...')
        print('  ' + stack[-1])

    print()
