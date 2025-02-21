# django-xformula

A dynamic query evaluator for [Django](https://www.djangoproject.com/)
applications.

## Table of Contents

- [Overview](#overview)
  - [Use Cases](#use-cases)
  - [Features](#features)
    - [Bidirectional Operators](#bidirectional-operators)
    - [Zero Built-in Variables by Default](#zero-built-in-variables-by-default)
    - [Customizable Attribute Getter](#customizable-attribute-getter)
    - [Customizable Function Caller](#customizable-function-caller)
- [Installation](#installation)
- [Usage](#usage)
- [Operators](#operators)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Overview

django-xformula is a powerful and flexible query evaluator designed for Django
applications. Built on top of the [XFormula](https://github.com/ertgl/xformula)
language front-end, it enables developers to transform formulas into Django ORM
query expressions. Its dynamic evaluation capabilities simplify having a DSL to
define complex queries, making it easier to build advanced features.

Whether you're building customizable APIs, implementing rule-based
authorization, or enabling dynamic data filtering, django-xformula
helps to create efficient solutions.

### Use Cases

Various applications can benefit from the dynamic query evaluation provided by
django-xformula. Here are a few examples:

- **Open APIs**: Enable external clients and integrated services to filter,
  annotate or aggregate data using intuitive formulas.
- **Authorization Rules**: Implement query-based authorization rules that are
  stored and managed directly in the database.
- **Dynamic Business Rules**: Hot-swap business rules without redeploying
  the application, allowing some departments to define and manage their
  own rules.
- **Personalized Experiences**: Allow users to customize their interactions
  with the application through dynamic queries. E.g. pre-filtering, sorting,
  conditional webhooks, etc.

The flexibility of django-xformula makes it suitable for many other scenarios
where dynamic query evaluation is required.

### Features

django-xformula provides minimal yet powerful features that enable developers
to build complex query evaluators for their specific needs.

#### Bidirectional Operators

django-xformula uses the same syntax for both Python and Django query
evaluations. Expressions are intelligently interpreted based on their content:

- When a `QuerySet` is present, the expression is evaluated as a `QuerySet`.
- When a `Q` object is involved, it is evaluated as a `Q`.
- If the expression includes a `Combinable` or `Field`, it will be processed as
  a `Combinable`.
- For expressions containing a model instance, the evaluator returns a `Value`
  holding the instance's primary key.
- All other operations are handled using standard Python evaluation rules.

#### Zero Built-in Variables by Default

By default, any variable referenced in a formula that is not explicitly defined
within the built-in context is treated as an `F` object. This ensures that only
approved variables and functions are used in query evaluations, preventing
potential security risks.

#### Customizable Attribute Getter

By default, accessing an object's attribute within a formula is prohibited and
will raise a `ForbiddenAttribute` error (a subclass of Django's
`PermissionDenied`). This behavior can be customized to specify which
attributes are accessible in formulas, adding an extra layer of security.

#### Customizable Function Caller

Function calls within formulas are restricted by default, raising a
`ForbiddenCall` error (inheriting from Django's `PermissionDenied`) if invoked.
The function caller can be customized to allow specific functions, balancing
flexibility with security.

## Installation

django-xformula is available on `PyPI`. You can install it using a compatible
package manager, such as `pip`:

```sh
pip install django-xformula
```

## Usage

Using django-xformula in your Django application is straightforward. The
following example demonstrates how to filter a Django queryset using a
user-supplied formula.

```py
from operator import call

from django.db.models import Q, QuerySet
from django.db.models.functions import Length
from django_xformula import QueryEvaluator

# Import your models
from myapp.models import MyModel


def resource_view(request):
    evaluator = QueryEvaluator()
    query = request.GET.get("q", "")
    context = QueryEvaluator.Context(
      # Provide Python objects to the formula context.
      builtins={
        "Length": Length,
        "me": request.user,
      },
      # WARNING: Allowing arbitrary function calls can be dangerous.
      # It is highly recommended to implement a secure function caller.
      # E.g. checking if the function is in a whitelist.
      call=call,
      # WARNING: Direct attribute access is unsafe.
      # Implement a secure attribute getter based on your requirements.
      # E.g. checking if the object or attribute is in a whitelist.
      getattr=getattr,
    )
    q_or_result = evaluator.evaluate(q, context)
    if isinstance(q_or_result, QuerySet):
        return render_table(q_or_result)
    if isinstance(q_or_result, Q):
        queryset = MyModel.objects.filter(q_or_result)
        return render_table(queryset)
    # If the formula does not represent a database query,
    # return the result of the evaluated expression (e.g., "1 + 1").
    return render_result(q_or_result)
```

In this example, users can filter `MyModel` instances using formulas that
reference the current user via the `me` variable.

See the following sample formulas to get an idea of what you can achieve:

- Get all records where `owner` is the current user:

  ```python
  owner is me
  ```

- Get all records where `owner` is not the current user:

  ```python
  owner is not me
  ```

- Get records where `name` has more than `5` characters:

  ```python
  Length(name) > 5
  ```

- Get the records if the current user is either an staff member or the owner,
  or the record is public:

  ```python
  me.is_staff or me is owner or is_public
  ```

- Get the records where the version is the current version, only if the
  condition is met before querying the database:

  ```python
  check_condition() and version is CURRENT_VERSION
  ```

### Operators

For a full list of supported operators, see the
[XFormula default precedence list](https://github.com/ertgl/xformula/blob/main/src/xformula/syntax/core/operations/default_operator_precedences.py#L16).

### Troubleshooting

When using django-xformula, you may encounter issues related to query syntax,
attribute access, or function calls. Here are some common issues and solutions:

- **Issue**: `ForbiddenAttribute` error when accessing an attribute.
  - **Solution**: Ensure that the attribute is allowed in the custom attribute
    getter.

- **Issue**: `ForbiddenCall` error when calling a function.
  - **Solution**: Ensure that the function is allowed in the custom function
    caller.

- **Issue**: Invalid query syntax.
  - **Solution**: Verify that the formula syntax follows the default grammar
    provided by XFormula.

- **Issue**: Unsupported database function.
  - **Solution**: Check if the database backend supports the database function
    being used in the query.

## License

This project is licensed under the
[MIT License](https://opensource.org/license/mit).

See the [LICENSE](LICENSE) file for more information.
