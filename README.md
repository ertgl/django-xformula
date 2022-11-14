# django-xformula

Django query evaluator, is built on top of XFormula language front-end.

---

**This project is still in development**.

If you're interested, you may check the note in
[XFormula](https://github.com/ertgl/xformula) repository.

---


## Features:

- Bidirectional operators
- - Same syntax for both Python and Django query evaluation
- - Operations contain at least one `QuerySet`, will be evaluated as `QuerySet`
- - Operations contain at least one `Q`, will be evaluated as `Q`
- - Operations contain at least one `Combinable`, will be evaluated as `Combinable`
- - Operations contain at least one `Field`, will be evaluated as `Combinable`
- - Operations contain at least one `Model` instance, will be evaluated as `Value`
    which contains the model instance's primary key
- - Other operations work like how Python does
- Zero built-in variable by default
- - When a variable name is used but does not exist in the specified built-ins,
    it will be evaluated as `F` object
- Customizable attribute getter; manage which attributes can be used in formulas
  (Getting an attribute of an object is forbidden by default, and raises
  `ForbiddenAttribute` error which inherits Django's `PermissionDenied` class)
- Customizable caller; manage which functions can be called in formulas
  (Calling a callable is forbidden by default, and raises `ForbiddenCall` error
  which inherits Django's `PermissionDenied` class)


## License

[MIT](https://github.com/ertgl/django-xformula/blob/main/LICENSE)
