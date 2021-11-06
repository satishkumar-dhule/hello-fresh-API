### Overview
Create a menu planning service which allows to manage weekly menu and associated recipies. 

#### Context
- A [weekly menu](https://www.hellofresh.com.au/plans/) contains a set of [recipies](https://www.hellofresh.com.au/recipes/). Each week different set of recipies are selected. See example [menu for this week](https://www.hellofresh.com.au/plans/).
- A [recipe](https://www.hellofresh.com.au/recipes/beef-veggie-ragu-spaghetti-5fa9c324cb8f8c0b3a183d01) contains ingredients, step-by-step instructions, nutirtional information, classification, and other metadata. See examples recipes here [1](https://www.hellofresh.com.au/recipes/southeast-asian-chicken-coconut-soup-5fa9c26209c8db59115d3f4f), [2](https://www.hellofresh.com.au/recipes/saucy-coconut-chicken-noodles-5f9b3c7198ecf4455b27d94d), [3](https://www.hellofresh.com.au/recipes/dukkah-roasted-sweet-potato-5f9b43847aacaa50f037d858).
- A customer can review weekly menu as well as recipe by assigning ratings and/or adding comments.

#### Tasks

1. Create data models using your selected ORM for weekly menu, recipe, ingredients, review, etc. Make sure these data models are appripriately connected using `FK`, `1:M`, `M:M ` relationships.
2. Create REST APIs to create, list, read, update, delete data model objects. Bonus if you can secure API using API tokens (recommended) or JWT tokens. You can use Google Authentication to obtain JWT token.
3. Create unit and E2E tests. For E2E API tests you can use [Postman](https://www.postman.com/) but ensure Postman collection are commited to your repository. For unit tests use a framework acccording to your stack.
4. Make sure your tests can be run from a single command - create test runner `makefile` or `bash` script to run your tests.


### Technology Stack
Python 3, Flask as web framework, PeeWee as ORM, Docker as Container, PostgreSQL as a database, Pytest for unit test, Postman for API test

### Features
Authorization using JWT
CRUD on all model items
Auto-setup of postgre and web-tier using docker
End to end testing using postman
Logging
Unit testing

### How to Run
- Execute setup.sh which will set up all docker stack and bring up the environment.

    ![Screenshot](docs/setup.png)

- After successful setup you should see web and db tier running in Docker.

    ![Screenshot](docs/docker-stack.png)

- To bring up the system you can use below command.

    ![Screenshot](docs/bringup.png)

- To bring up the system in dettached mode you can use below command.

    ![Screenshot](docs/bringup-dettached.png)

- To bring down the system you can use below command.

    ![Screenshot](docs/bringdown.png)


### API Testing


- Sample Pytest results.

    ![Screenshot](docs/test.png)


- API documentation is published on postman https://documenter.getpostman.com/view/7952247/UVC2HoyV
- 
    ![Screenshot](docs/api-test.png)
