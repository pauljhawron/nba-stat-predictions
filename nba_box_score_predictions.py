
# Import Packages

# Getting Data
from urllib.request import urlopen
from bs4 import BeautifulSoup
import requests
import pandas as pd
from flask import Flask, render_template, request

# UI
app = Flask(__name__)

# Get Data - Per Game For Teams & Players

# URLs to scrape
team_url = 'https://www.basketball-reference.com/leagues/NBA_2024.html'
basic_player_url = 'https://www.basketball-reference.com/leagues/NBA_2024_per_game.html'
advanced_player_url = 'https://www.basketball-reference.com/leagues/NBA_2024_advanced.html'

# Get team stats
page = requests.get(team_url)
page = page.text.replace('<!--','').replace('-->','')
soup = BeautifulSoup(page, 'html.parser')

soup_team = soup.find('table', id='per_game-team')
soup_opponent = soup.find('table', id='per_game-opponent')

# Get basic player stats
page = requests.get(basic_player_url)
page = page.text.replace('<!--','').replace('-->','')
soup = BeautifulSoup(page, 'html.parser')

soup_basic_player = soup.find('table', id='per_game_stats')

# Get advanced player stats
page = requests.get(advanced_player_url)
page = page.text.replace('<!--','').replace('-->','')
soup = BeautifulSoup(page, 'html.parser')

soup_advanced_player = soup.find('table', id='advanced_stats')

# Convert BeautifulSoup objects to Pandas DataFrames
df_team = pd.read_html(str(soup_team))[0]
df_opponent = pd.read_html(str(soup_opponent))[0]
df_basic_player = pd.read_html(str(soup_basic_player))[0]
df_advanced_player = pd.read_html(str(soup_advanced_player))[0]

"""# Manipulate Data"""

# The player tables have recurring headers that need to be dropped
df_basic_player = df_basic_player[df_basic_player.Rk != 'Rk']
df_advanced_player = df_advanced_player[df_advanced_player.Rk != 'Rk']

# Map the team name abbreviations to full team names so that we can join these two tables
team_mapping = {
    'Team Abbreviation': [
        'ATL', 'BOS', 'BRK', 'CHO', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW',
        'HOU', 'IND', 'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN', 'NOP', 'NYK',
        'OKC', 'ORL', 'PHI', 'PHO', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS'
    ],
    'Team Name': [
        'Atlanta Hawks', 'Boston Celtics', 'Brooklyn Nets', 'Charlotte Hornets', 'Chicago Bulls',
        'Cleveland Cavaliers', 'Dallas Mavericks', 'Denver Nuggets', 'Detroit Pistons', 'Golden State Warriors',
        'Houston Rockets', 'Indiana Pacers', 'Los Angeles Clippers', 'Los Angeles Lakers', 'Memphis Grizzlies',
        'Miami Heat', 'Milwaukee Bucks', 'Minnesota Timberwolves', 'New Orleans Pelicans', 'New York Knicks',
        'Oklahoma City Thunder', 'Orlando Magic', 'Philadelphia 76ers', 'Phoenix Suns', 'Portland Trail Blazers',
        'Sacramento Kings', 'San Antonio Spurs', 'Toronto Raptors', 'Utah Jazz', 'Washington Wizards'
    ]
}

df_team_mapping = pd.DataFrame(team_mapping)

# Merge DataFrames with the new mapper to have matching columns
df_basic_player = df_basic_player.merge(df_team_mapping, left_on='Tm', right_on='Team Abbreviation', how='left')
df_advanced_player = df_advanced_player.merge(df_team_mapping, left_on='Tm', right_on='Team Abbreviation', how='left')
df_team = df_team.merge(df_team_mapping, left_on='Team', right_on='Team Name', how='left')
df_opponent = df_opponent.merge(df_team_mapping, left_on='Team', right_on='Team Name', how='left')

# Drop original columns for consistency
df_basic_player = df_basic_player.drop('Tm', axis=1)
df_advanced_player = df_advanced_player.drop('Tm', axis=1)
df_team = df_team.drop('Team', axis=1)
df_opponent = df_opponent.drop('Team', axis=1)

# Create new DataFrames to merge together and drop the columns we aren't worried about right now
df_player_merge = df_basic_player.drop(['Rk', 'Pos', 'Age', 'MP', 'G', 'GS', 'FG%', '3P%', '2P', '2PA', '2P%', 'eFG%', 'FT', 'FTA', 'FT%', 'ORB', 'DRB'], axis=1)
df_team_merge = df_team.drop(['Rk', 'G', 'MP', 'FG%', '3P%', '2P', '2PA', '2P%', 'FT', 'FTA', 'FT%', 'ORB', 'DRB'], axis=1)
df_opponent_merge = df_opponent.drop(['Rk', 'G', 'MP', 'FG%', '3P%', '2P', '2PA', '2P%', 'FT', 'FTA', 'FT%', 'ORB', 'DRB'], axis=1)

# Adding prefixes for when we join the DataFrames together
df_player_merge = df_player_merge.rename(columns={c: 'player_'+c for c in df_player_merge.columns if c not in ['Team Abbreviation', 'Team Name', 'Player']})
df_team_merge = df_team_merge.rename(columns={c: 'team_'+c for c in df_team_merge.columns if c not in ['Team Abbreviation', 'Team Name']})
df_opponent_merge = df_opponent_merge.rename(columns={c: 'opponent_'+c for c in df_opponent_merge.columns if c not in ['Team Abbreviation', 'Team Name']})

# Merge DataFrames together
df_player_merge = df_player_merge.merge(df_team_merge, on=['Team Abbreviation', 'Team Name'], how='inner')
df_team_merge = df_team_merge.merge(df_opponent_merge, on=['Team Abbreviation', 'Team Name'], how='inner')

# Creating a new DataFrame that calculates the players' share of team stats
df_player_pct = pd.DataFrame({
    'player': df_player_merge['Player']
    , 'team_abbreviation': df_player_merge['Team Abbreviation']
    , 'team_name': df_player_merge['Team Name']
    , '%_of_team_FG': df_player_merge['player_FG'].astype(float) / df_player_merge['team_FG'].astype(float)
    , '%_of_team_FGA': df_player_merge['player_FGA'].astype(float) / df_player_merge['team_FGA'].astype(float)
    , '%_of_team_3P': df_player_merge['player_3P'].astype(float) / df_player_merge['team_3P'].astype(float)
    , '%_of_team_3PA': df_player_merge['player_3PA'].astype(float) / df_player_merge['team_3PA'].astype(float)
    , '%_of_team_TRB': df_player_merge['player_TRB'].astype(float) / df_player_merge['team_TRB'].astype(float)
    , '%_of_team_AST': df_player_merge['player_AST'].astype(float) / df_player_merge['team_AST'].astype(float)
    , '%_of_team_STL': df_player_merge['player_STL'].astype(float) / df_player_merge['team_STL'].astype(float)
    , '%_of_team_BLK': df_player_merge['player_BLK'].astype(float) / df_player_merge['team_BLK'].astype(float)
    , '%_of_team_TOV': df_player_merge['player_TOV'].astype(float) / df_player_merge['team_TOV'].astype(float)
    , '%_of_team_PF': df_player_merge['player_PF'].astype(float) / df_player_merge['team_PF'].astype(float)
    , '%_of_team_PTS': df_player_merge['player_PTS'].astype(float) / df_player_merge['team_PTS'].astype(float)
})

# UI
@app.route('/')
def index():
    # Pass the list of teams to the HTML template
    team_list = df_team_mapping['Team Name'].tolist()
    return render_template('index.html', team_list=team_list)

@app.route('/predictions', methods=['POST'])
def predictions():
    # Get the selected teams from the form
    team_1 = request.form.get('team1')
    team_2 = request.form.get('team2')

    """# Predict Matchup Stats"""

    # Get two teams selected by user
    df_team_1 = df_team_merge[df_team_merge['Team Name'] == team_1]
    df_team_2 = df_team_merge[df_team_merge['Team Name'] == team_2]

    df_team_1_projections = pd.DataFrame({
        'team_name': team_1
        , 'opponent_name': team_2
        , 'predicted_FG': (df_team_1.iloc[0]['team_FG'].astype(float) + df_team_2.iloc[0]['opponent_FG'].astype(float)) / 2
        , 'predicted_FGA': (df_team_1.iloc[0]['team_FGA'].astype(float) + df_team_2.iloc[0]['opponent_FGA'].astype(float)) / 2
        , 'predicted_3P': (df_team_1.iloc[0]['team_3P'].astype(float) + df_team_2.iloc[0]['opponent_3P'].astype(float)) / 2
        , 'predicted_3PA': (df_team_1.iloc[0]['team_3PA'].astype(float) + df_team_2.iloc[0]['opponent_3PA'].astype(float)) / 2
        , 'predicted_TRB': (df_team_1.iloc[0]['team_TRB'].astype(float) + df_team_2.iloc[0]['opponent_TRB'].astype(float)) / 2
        , 'predicted_AST': (df_team_1.iloc[0]['team_AST'].astype(float) + df_team_2.iloc[0]['opponent_AST'].astype(float)) / 2
        , 'predicted_STL': (df_team_1.iloc[0]['team_STL'].astype(float) + df_team_2.iloc[0]['opponent_STL'].astype(float)) / 2
        , 'predicted_BLK': (df_team_1.iloc[0]['team_BLK'].astype(float) + df_team_2.iloc[0]['opponent_BLK'].astype(float)) / 2
        , 'predicted_TOV': (df_team_1.iloc[0]['team_TOV'].astype(float) + df_team_2.iloc[0]['opponent_TOV'].astype(float)) / 2
        , 'predicted_PF': (df_team_1.iloc[0]['team_PF'].astype(float) + df_team_2.iloc[0]['opponent_PF'].astype(float)) / 2
        , 'predicted_PTS': (df_team_1.iloc[0]['team_PTS'].astype(float) + df_team_2.iloc[0]['opponent_PTS'].astype(float)) / 2
    }, index=[0])

    df_team_2_projections = pd.DataFrame({
        'team_name': team_2
        , 'opponent_name': team_1
        , 'predicted_FG': (df_team_2.iloc[0]['team_FG'].astype(float) + df_team_1.iloc[0]['opponent_FG'].astype(float)) / 2
        , 'predicted_FGA': (df_team_2.iloc[0]['team_FGA'].astype(float) + df_team_1.iloc[0]['opponent_FGA'].astype(float)) / 2
        , 'predicted_3P': (df_team_2.iloc[0]['team_3P'].astype(float) + df_team_1.iloc[0]['opponent_3P'].astype(float)) / 2
        , 'predicted_3PA': (df_team_2.iloc[0]['team_3PA'].astype(float) + df_team_1.iloc[0]['opponent_3PA'].astype(float)) / 2
        , 'predicted_TRB': (df_team_2.iloc[0]['team_TRB'].astype(float) + df_team_1.iloc[0]['opponent_TRB'].astype(float)) / 2
        , 'predicted_AST': (df_team_2.iloc[0]['team_AST'].astype(float) + df_team_1.iloc[0]['opponent_AST'].astype(float)) / 2
        , 'predicted_STL': (df_team_2.iloc[0]['team_STL'].astype(float) + df_team_1.iloc[0]['opponent_STL'].astype(float)) / 2
        , 'predicted_BLK': (df_team_2.iloc[0]['team_BLK'].astype(float) + df_team_1.iloc[0]['opponent_BLK'].astype(float)) / 2
        , 'predicted_TOV': (df_team_2.iloc[0]['team_TOV'].astype(float) + df_team_1.iloc[0]['opponent_TOV'].astype(float)) / 2
        , 'predicted_PF': (df_team_2.iloc[0]['team_PF'].astype(float) + df_team_1.iloc[0]['opponent_PF'].astype(float)) / 2
        , 'predicted_PTS': (df_team_2.iloc[0]['team_PTS'].astype(float) + df_team_1.iloc[0]['opponent_PTS'].astype(float)) / 2
    }, index=[0])

    # Predict player statlines
    df_team_1_players = df_player_pct[df_player_pct['team_name'] == team_1]
    df_team_2_players = df_player_pct[df_player_pct['team_name'] == team_2]

    # Merge in the team's projections so that we can use that to derive player projections
    df_team_1_projection_merge = df_team_1_players.merge(df_team_1_projections, on=['team_name'], how='inner')
    df_team_2_projection_merge = df_team_2_players.merge(df_team_2_projections, on=['team_name'], how='inner')

    # Creating new columns with player projections
    df_team_1_projection_merge['player_predicted_FG'] = df_team_1_projection_merge['%_of_team_FG'] * df_team_1_projection_merge['predicted_FG']
    df_team_1_projection_merge['player_predicted_FGA'] = df_team_1_projection_merge['%_of_team_FGA'] * df_team_1_projection_merge['predicted_FGA']
    df_team_1_projection_merge['player_predicted_3P'] = df_team_1_projection_merge['%_of_team_3P'] * df_team_1_projection_merge['predicted_3P']
    df_team_1_projection_merge['player_predicted_3PA'] = df_team_1_projection_merge['%_of_team_3PA'] * df_team_1_projection_merge['predicted_3PA']
    df_team_1_projection_merge['player_predicted_TRB'] = df_team_1_projection_merge['%_of_team_TRB'] * df_team_1_projection_merge['predicted_TRB']
    df_team_1_projection_merge['player_predicted_AST'] = df_team_1_projection_merge['%_of_team_AST'] * df_team_1_projection_merge['predicted_AST']
    df_team_1_projection_merge['player_predicted_STL'] = df_team_1_projection_merge['%_of_team_STL'] * df_team_1_projection_merge['predicted_STL']
    df_team_1_projection_merge['player_predicted_BLK'] = df_team_1_projection_merge['%_of_team_BLK'] * df_team_1_projection_merge['predicted_BLK']
    df_team_1_projection_merge['player_predicted_TOV'] = df_team_1_projection_merge['%_of_team_TOV'] * df_team_1_projection_merge['predicted_TOV']
    df_team_1_projection_merge['player_predicted_PF'] = df_team_1_projection_merge['%_of_team_PF'] * df_team_1_projection_merge['predicted_PF']
    df_team_1_projection_merge['player_predicted_PTS'] = df_team_1_projection_merge['%_of_team_PTS'] * df_team_1_projection_merge['predicted_PTS']

    df_team_2_projection_merge['player_predicted_FG'] = df_team_2_projection_merge['%_of_team_FG'] * df_team_2_projection_merge['predicted_FG']
    df_team_2_projection_merge['player_predicted_FGA'] = df_team_2_projection_merge['%_of_team_FGA'] * df_team_2_projection_merge['predicted_FGA']
    df_team_2_projection_merge['player_predicted_3P'] = df_team_2_projection_merge['%_of_team_3P'] * df_team_2_projection_merge['predicted_3P']
    df_team_2_projection_merge['player_predicted_3PA'] = df_team_2_projection_merge['%_of_team_3PA'] * df_team_2_projection_merge['predicted_3PA']
    df_team_2_projection_merge['player_predicted_TRB'] = df_team_2_projection_merge['%_of_team_TRB'] * df_team_2_projection_merge['predicted_TRB']
    df_team_2_projection_merge['player_predicted_AST'] = df_team_2_projection_merge['%_of_team_AST'] * df_team_2_projection_merge['predicted_AST']
    df_team_2_projection_merge['player_predicted_STL'] = df_team_2_projection_merge['%_of_team_STL'] * df_team_2_projection_merge['predicted_STL']
    df_team_2_projection_merge['player_predicted_BLK'] = df_team_2_projection_merge['%_of_team_BLK'] * df_team_2_projection_merge['predicted_BLK']
    df_team_2_projection_merge['player_predicted_TOV'] = df_team_2_projection_merge['%_of_team_TOV'] * df_team_2_projection_merge['predicted_TOV']
    df_team_2_projection_merge['player_predicted_PF'] = df_team_2_projection_merge['%_of_team_PF'] * df_team_2_projection_merge['predicted_PF']
    df_team_2_projection_merge['player_predicted_PTS'] = df_team_2_projection_merge['%_of_team_PTS'] * df_team_2_projection_merge['predicted_PTS']

    # Creating new DataFrame with final stats of interest for player predictions
    df_team_1_player_projections = pd.DataFrame({
        'Player': df_team_1_projection_merge['player']
        , 'Points': df_team_1_projection_merge['player_predicted_PTS']
        , 'Rebounds': df_team_1_projection_merge['player_predicted_TRB']
        , 'Asssists': df_team_1_projection_merge['player_predicted_AST']
        , 'Steals': df_team_1_projection_merge['player_predicted_STL']
        , 'Blocks': df_team_1_projection_merge['player_predicted_BLK']
        , 'Turnovers': df_team_1_projection_merge['player_predicted_TOV']
        , 'Personal Fouls': df_team_1_projection_merge['player_predicted_PF']
        , 'Field Goals Made': df_team_1_projection_merge['player_predicted_FG']
        , 'Field Goals Attempted': df_team_1_projection_merge['player_predicted_FGA']
        , '3-Pointers Made': df_team_1_projection_merge['player_predicted_3P']
        , '3-Pointers Attempted': df_team_1_projection_merge['player_predicted_3PA']
        , 'PTS + REB + AST': df_team_1_projection_merge['player_predicted_PTS'] + df_team_1_projection_merge['player_predicted_TRB'] + df_team_1_projection_merge['player_predicted_AST']
        , 'REB + AST': df_team_1_projection_merge['player_predicted_TRB'] + df_team_1_projection_merge['player_predicted_AST']
        , 'PTS + REB': df_team_1_projection_merge['player_predicted_PTS'] + df_team_1_projection_merge['player_predicted_TRB']
        , 'PTS + AST': df_team_1_projection_merge['player_predicted_PTS'] + df_team_1_projection_merge['player_predicted_AST']
        , 'STL + BLK': df_team_1_projection_merge['player_predicted_STL'] + df_team_1_projection_merge['player_predicted_BLK']
    })

    df_team_2_player_projections = pd.DataFrame({
        'Player': df_team_2_projection_merge['player']
        , 'Points': df_team_2_projection_merge['player_predicted_PTS']
        , 'Rebounds': df_team_2_projection_merge['player_predicted_TRB']
        , 'Asssists': df_team_2_projection_merge['player_predicted_AST']
        , 'Steals': df_team_2_projection_merge['player_predicted_STL']
        , 'Blocks': df_team_2_projection_merge['player_predicted_BLK']
        , 'Turnovers': df_team_2_projection_merge['player_predicted_TOV']
        , 'Personal Fouls': df_team_2_projection_merge['player_predicted_PF']
        , 'Field Goals Made': df_team_2_projection_merge['player_predicted_FG']
        , 'Field Goals Attempted': df_team_2_projection_merge['player_predicted_FGA']
        , '3-Pointers Made': df_team_2_projection_merge['player_predicted_3P']
        , '3-Pointers Attempted': df_team_2_projection_merge['player_predicted_3PA']
        , 'PTS + REB + AST': df_team_2_projection_merge['player_predicted_PTS'] + df_team_2_projection_merge['player_predicted_TRB'] + df_team_2_projection_merge['player_predicted_AST']
        , 'REB + AST': df_team_2_projection_merge['player_predicted_TRB'] + df_team_2_projection_merge['player_predicted_AST']
        , 'PTS + REB': df_team_2_projection_merge['player_predicted_PTS'] + df_team_2_projection_merge['player_predicted_TRB']
        , 'PTS + AST': df_team_2_projection_merge['player_predicted_PTS'] + df_team_2_projection_merge['player_predicted_AST']
        , 'STL + BLK': df_team_2_projection_merge['player_predicted_STL'] + df_team_2_projection_merge['player_predicted_BLK']
    })

    # Define the columns to be rounded
    columns_to_round = df_team_1_player_projections.columns.difference(['Player'])

    # Apply rounding using the round() function to specified columns
    df_team_1_player_projections[columns_to_round] = df_team_1_player_projections[columns_to_round].apply(lambda x: round(x, 1))
    df_team_2_player_projections[columns_to_round] = df_team_2_player_projections[columns_to_round].apply(lambda x: round(x, 1))


    return render_template('predictions.html', team_1=team_1, team_2=team_2,
                           df_team_1_player_projections=df_team_1_player_projections,
                           df_team_2_player_projections=df_team_2_player_projections)

if __name__ == '__main__':
    app.run(debug=True)
