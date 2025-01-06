// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TournamentScores {
    struct Player {
        string name;
        uint256 score;
    }

    Player[] public players;
    string public tournamentName;
    address public admin;

    constructor(string memory _name, string[] memory _playerNames, uint256[] memory _playerScores) {
        require(_playerNames.length == _playerScores.length, "Players and scores length mismatch");

        tournamentName = _name;
        admin = msg.sender;

        for (uint256 i = 0; i < _playerNames.length; i++) {
            players.push(Player(_playerNames[i], _playerScores[i]));
        }
    }

    function getPlayer(uint256 index) public view returns (string memory, uint256) {
        require(index < players.length, "Index out of range");
        Player memory player = players[index];
        return (player.name, player.score);
    }
    
    function getPlayersCount() public view returns (uint256) {
        return players.length;
    }
}
