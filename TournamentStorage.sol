// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title TournamentStorage
 * @dev Store and retrieve tournament information
 */
contract TournamentStorage {
    // Struct to store tournament information
    struct Tournament {
        string name;
        address winner;
    }

    // Mapping from tournament ID to Tournament struct
    mapping(uint256 => Tournament) public tournaments;
    
    // Counter for tournament IDs
    uint256 private nextTournamentId = 1;
    
    // Event emitted when a new tournament is created
    event TournamentCreated(uint256 indexed tournamentId, string name, address winner);
    
    /**
     * @dev Add a new tournament to the storage
     * @param _name Name of the tournament
     * @param _winner Address of the tournament winner
     * @return tournamentId The ID of the newly created tournament
     */
    function addTournament(string memory _name, address _winner) public returns (uint256) {
        uint256 tournamentId = nextTournamentId;
        
        tournaments[tournamentId] = Tournament({
            name: _name,
            winner: _winner
        });
        
        nextTournamentId++;
        
        emit TournamentCreated(tournamentId, _name, _winner);
        
        return tournamentId;
    }
    
    /**
     * @dev Get details of a tournament by ID
     * @param _tournamentId The ID of the tournament to retrieve
     * @return name The name of the tournament
     * @return winner The address of the tournament winner
     */
    function getTournament(uint256 _tournamentId) public view returns (string memory name, address winner) {
        Tournament memory tournament = tournaments[_tournamentId];
        return (tournament.name, tournament.winner);
    }
    
    /**
     * @dev Get the current tournament count
     * @return The number of tournaments that have been created
     */
    function getTournamentCount() public view returns (uint256) {
        return nextTournamentId - 1;
    }
}

