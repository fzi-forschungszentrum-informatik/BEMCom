# The Building Energy Management Communication Framework (BEMCom)
Building Energy Management (BEM), here as active optimization of energy consumption patterns of buildings, is commonly expected to contribute a significant part to the stability of future electricity grids that have to cope with a high share of volatile generation from renewable sources. However, to practically apply such optimization it is necessary to interact with a potentially very diverse set of devices of the target building, including classical sensors (e.g. measuring temperature, humidity, $CO_2$, ...), HVAC systems (heating, ventilation, air conditioning) but also charge stations for electric vehicles.

In order to communicate with the devices of a target building, it is common in academia to implement a building specific application, that is able to communicate with all the devices, and that exposes a unified interface to allow upstream applications (like user interfaces or optimization algorithms) to interact with the devices over this interface. Implementing such applications, that are sometimes referred to as hardware abstraction layers (HALs), is a recurring pattern in BEM related research projects  that causes significant effort. BEMCom is designed to drastically reduce the effort for implementing and maintaining such HAL applications, please see the documentation for details.



## Documentation

The extensive online documentation can be found on [bemcom.readthedocs.io](https://bemcom.readthedocs.io/en/latest/index.html). 



## Contact

Please open a GitHub issue for any inquiry that relates to the source code. Feel free to contact [David Wölfle](https://www.fzi.de/team/david-woelfle/) directly for all other inquiries.



## Contributing

Contributions are welcome! Please see the [documented guidelines](https://bemcom.readthedocs.io/en/latest/04_contributing.html) before you start developing.



## Copyright and License

Code is copyright to the FZI Research Center for Information Technology and released under the MIT [license](./LICENSE).