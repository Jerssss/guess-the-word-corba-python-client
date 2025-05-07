class About:
    def display(self):
        about_text = """
        WHAT'S THE WORD?!
        Created by Team 1:
        ANG-ANGCO, JEREMIAH
        ESPERANZATE, ANJELO
        FLORES, GABRIEL ALYSON
        GRABANZOR, GIANA KRISTY
        MOLINA, BERNARD SEBASTHIAN
        TENORIO, KRISTELLE MAYE


        Game Description:
        WHAT'S THE WORD?! is an exciting and fast-paced multiplayer word-guessing game that gives a fresh twist to the classic Hangman format. Compete against friends and players to guess the mystery word before anyone else. The game is designed for quick thinking and rapid decision-making, offering a race against the clock to determine who can guess the word first.

        Gameplay Overview:
        The game revolves around rounds, with players trying to guess a hidden word based on a set of clues. With each round, you’ll have 30 seconds to figure out the word, but you only have five incorrect guesses—so think fast!

        The player who guesses the word in the shortest time wins the round. If no one guesses correctly by the end of the round, no winner is declared.


        How to Play:
        Game Initiation: Start a new game from the home screen. You can join with other players, but the game will begin if at least one player joins within 10 seconds. If no one joins, the initiating player will be notified and returned to the home screen.

        Rounds: Each game is made up of multiple rounds, and the first player to win three rounds wins the game.

        Round Mechanics:
        The server provides a word length as a clue.
        All players play simultaneously and are given five attempts to guess the word.
        Players take turns guessing one letter at a time, and correct guesses are revealed in their proper positions.
        Players can attempt to guess the entire word at any point—if correct, they win the round instantly.

        Winning a Round:
        The first player to guess the complete word wins the round.
        If multiple players guess the word correctly, the player who did so the fastest wins.
        If no one guesses correctly, the round ends with no winner.

        Word Selection: Words are randomly chosen from a file and are unique for each game. Words are never repeated within the same game.
        Player Actions:
        Players submit one letter at a time and receive feedback: positions where the letter appears or a notification for incorrect guesses.
        Players can guess the full word at any time during a round.

        Game End Conditions:
        The first player to win three rounds is crowned the overall winner.
        Once the game concludes, all players are returned to the home screen.

        Get ready to think fast, guess faster, and compete to be the ultimate word master in WHAT'S THE WORD?!
                """
        print(about_text)
