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
- - If an operation contains at least one `django.db.models.expressions.Combinable`
    or `django.db.models.Q` object, it will be evaluated as `django.db.models.Q`
    object
- Zero built-in variable by defaults
- - When a variable name is used but does not exist in the specified built-ins,
    it will be evaluated as `django.db.models.F` object
- Customizable attribute getter; manage which attributes can be used in formulas
  (Getting an attribute of an object is prohibited by default)
- Customizable caller; manage which functions can be called in formulas
  (Calling is prohibited by default)


## License

[MIT](https://github.com/ertgl/xformula/blob/main/LICENSE)
