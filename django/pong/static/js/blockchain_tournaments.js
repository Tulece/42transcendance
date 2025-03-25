function searchTournament() {
    const id = document.getElementById('tournamentId').value;
    if (!id) return;

    document.getElementById('tournamentCard').classList.add('d-none');
    document.getElementById('errorMessage').classList.add('d-none');

    fetch(`/api/blockchain/tournament/${id}/`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('tournamentCard').classList.remove('d-none');
                document.getElementById('tournamentName').textContent = data.data.name;
                document.getElementById('tournamentWinner').textContent = data.data.winner;
                document.getElementById('tournamentBlockchainId').textContent = data.data.tournament_id;
            } else {
                throw new Error(data.error);
            }
        })
        .catch(error => {
            const errorDiv = document.getElementById('errorMessage');
            errorDiv.textContent = `Erreur: ${error.message || 'Tournoi non trouvé'}`;
            errorDiv.classList.remove('d-none');
        });
}

function initBlockchainTournamentPage() {
    const searchBtn = document.querySelector('.btn-primary');
    searchBtn.onclick = searchTournament;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBlockchainTournamentPage);
} else {
    initBlockchainTournamentPage();
}
