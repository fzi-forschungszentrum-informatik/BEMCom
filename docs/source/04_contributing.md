# Contributing

Contributions are welcome, especially extensions to the documentation and new services. Please follow the guide provided below to ensure that your work will fit into this repo. Please feel free to open up an issue to discuss your ideas before starting to work on something.



## Developing Services

Any BEMCom application can easily be extended with new services. If you plan to contribute a service to this repository please ensure you have considered the following points:

* [ ] That you have understood the [fundamental concepts](./01_concepts.md) of BEMCom before you start.
* [ ] That you use one of the [service templates](../service_templates/) if one exists for the service type and programming language. Please also consider to develop a service template if none exists but it would make sense. E.g. consider e.g. that you would like to implement a connector in a programming language for which no template exists. Splitting up the new connector into a template and the connector itself will likely introduce little overhead to the first connector, but will significantly reduce development effort for the second connector using the same programming language.
* [ ] That you have read and understood the [message format](./04_message_format.md) before you start if you plan to implement a service template or a service that should directly interact with the broker. Also please verify that you will implemented the message format correctly and completely.



## Implementation Rules

Here additional rules for for implementations in specific programming languages.

### Python

Please follow these guidelines while implementing components in Python:

* **Readability counts! Thus, before you start:** Read and understand [PEP 8](https://www.python.org/dev/peps/pep-0008/).
* **Documentation is Key:** Try to document <u>why</u> stuff is done. Furthermore document <u>what</u> is done if that is not obvious from the code. 
* **Docstrings:** Every function/method/class should have a Docstring following the [Numpy convention](https://numpydoc.readthedocs.io/en/latest/format.html).
* **Provide tests for everything:** Tests ensure that your code can be maintained and is not thrown away after the first bug is encountered. Unless you have very good reason, use [pytest](https://docs.pytest.org/).
* **Use the right format:** Use [Black](https://github.com/psf/black) to format your code. Maximum line length is 80 characters.

Code will only be accepted to merge if it is:

* **Formally correct:** [Flake8](https://flake8.pycqa.org/en/latest/) shows no errors or warnings. Again using a maximum line length of 80 characters.
* **Logically correct:** All tests pass and all relevant aspects of the code are tested.
