# Fantasy La Liga Predictor

Fantasy La Liga Predictor is a machine learning model that provides users with accurate and timely recommendations on which players to purchase and at what price, ultimately helping users to create a winning Fantasy team for the Spanish football league, La Liga.

## Architecture

The architecture pipeline of the project is as follows:

1. **Data Extraction**: Extract data from Fantasy LaLiga API with Lambda Function
2. **Data Storage**: Store raw data on S3
3. **Data Transformation**: This triggers a function app that initializes a Sagemaker Notebook to transform the data by cleaning and performing feature engineering and storing this final dataset on S3
4. **Model Training**: Train model using SageMaker and save it on S3
5. **Model Deployment**: Deploy model to a SageMaker Serverless instance

## Features

The model uses the following features to predict the performance of a player in the next match:

- Average number of points earned in the last 5 matches
- Total number of goals scored in the last 5 matches
- Average number of minutes played in the last 5 matches
- Number of previous injuries
- Average number of points earned at home
- Average number of points earned away

## Usage

To use the model, access the website at http://54.144.240.197:8501/ and enter the name or ID of the player. The model will return a recommendation on whether to buy or not based on the player's predicted performance in the next match.

## Contributors

- [Quique Mendez](https://github.com/quiquemz)
- [Juliette Navarre](https://www.linkedin.com/in/juliette-navarre/)
- [Ka Ho Wan](https://www.linkedin.com/in/terrancewankaho/)
- [Bob Bury](https://www.linkedin.com/in/bob-bury-/)
- [Liza Shaban](https://www.linkedin.com/in/liza-shaban-%F0%9F%87%BA%F0%9F%87%A6-791336190/)



## License

This project is licensed under the terms of the MIT license.
