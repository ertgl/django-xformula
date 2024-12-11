# django-xformula

Django query evaluator, built on top of
[XFormula](https://github.com/ertgl/xformula) language front-end.

## Use Cases

This library can be used to develop various types of features, such as:

* **Open APIs**: Allow users and integrated services to filter data using formulas
* **Flexible Security**: Implement query-based authorization checks, stored in the database
* **Conditional Webhooks**: Trigger webhooks based on preferred conditions, likely provided by the user
* **Personalized Experience**: Allow users to customize their interactions with the app

These are just a few examples of what you can do with `django-xformula`.

## Features

* **Bidirectional operators**
  * Same syntax for both Python and Django query evaluation
  * Operations containing at least one `QuerySet` will be evaluated as `QuerySet`
  * Operations containing at least one `Q` will be evaluated as `Q`
  * Operations containing at least one `Combinable` will be evaluated as `Combinable`
  * Operations containing at least one `Field` will be evaluated as `Combinable`
  * Operations containing at least one `Model` instance will be evaluated as `Value` containing the model instance's primary key
  * Other operations work like Python

* **Zero built-in variables by default**
  * When a variable name is used but does not exist in the specified built-ins, it will be evaluated as an `F` object

* **Customizable attribute getter**
  * Manage which attributes can be used in formulas (Getting an attribute of an object is forbidden by default and raises a `ForbiddenAttribute` error which inherits Django's `PermissionDenied` class)

* **Customizable caller**
  * Manage which functions can be called in formulas (Calling a callable is forbidden by default and raises a `ForbiddenCall` error which inherits Django's `PermissionDenied` class)

## Installation

To install `django-xformula`, use the following command:

```sh
pip install django-xformula
```

## Usage

Here's a basic, unsafe, pseudo example of how to use `django-xformula`.
This code snippet demonstrates how to filter a Django queryset using a
formula provided by the user:

```py
from operator import call

from django.db.models import Q, QuerySet
from django.db.models.functions import Length
from django_xformula import QueryEvaluator

# Import your models here
from myapp.models import MyModel


def resource_view(request):
    evaluator = QueryEvaluator()
    query = request.GET.get("q", "")
    context = QueryEvaluator.Context(
      # Pass Python objects to the formula context.
      builtins={
        "Length": Length,
        "me": request.user,
      },
      # Very dangerous! Do not use in production!
      # Better to write your own function caller
      # based on the conditions you want to allow or disallow.
      call=call,
      # Very dangerous! Do not use in production!
      # Better to write your own attribute getter
      # based on the conditions you want to allow or disallow.
      getattr=getattr,
    )
    q_or_result = evaluator.evaluate(q, context)
    if isinstance(q_or_result, QuerySet):
        return render_table(q_or_result)
    if isinstance(q_or_result, Q):
        queryset = MyModel.objects.filter(q_or_result)
        return render_table(queryset)
    # Probably, the formula was not a database query.
    # The evaluator has returned the result of the formula.
    # E.g.: Expressions like `1 + 1`, etc...
    return render_result(q_or_result)
```

This endpoint would allow users to filter `MyModel` instances using formulas
containing the `me` variable, which is the current user.

For example, the following query would return all `MyModel` instances where the
`owner_id` field is equal to the current user's ID:

```python
owner_id == me.id
```

Another example would be to return all `MyModel` instances where the `name`
field is longer than 5 characters:

```python
Length(name) > 5
```

Even more complex queries can be written, such as the following example.
This query would return all `MyModel` instances where the `name` field is longer
than field `age`, only if the remote data is fetched successfully:

```python
fetch_remote_data(me).status_code == 200 and Length(name) > age
```

### Operators

XFormula supports a wide range of operators by default, Python operators are
included as well. See the
[default operator precedences](https://github.com/ertgl/xformula/blob/main/src/xformula/syntax/core/operations/default_operator_precedences.py#L16)
for more information.

### Query Validity

Django ORM's rules still apply. Do not allow users to execute database
functions that are not supported by your database backend.

## License

This project is licensed under the
[MIT License](https://opensource.org/license/mit).

See the [LICENSE](LICENSE) file for more information.
