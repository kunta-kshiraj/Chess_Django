document.addEventListener("DOMContentLoaded", function () {
    function fetchAvailableUsersAndChallenges() {
        const url = document.getElementById('pollAvailableUsersUrl').value;

        fetch(url)
            .then(response => response.json())
            .then(data => {
                const usersList = document.querySelector('.list-group');  // Find the list group
                usersList.innerHTML = '';  // Clear the current list

                // Iterate over the active users and build the list with challenge buttons
                data.active_users.forEach(user => {
                    let li = document.createElement('li');
                    li.classList.add('list-group-item', 'd-flex', 'justify-content-between', 'align-items-center');
                    li.innerText = user.username;

                    // Check if there is a pending challenge from this user
                    if (user.has_challenge === 'received') {
                        // Accept/Reject buttons for received challenges
                        let acceptBtn = document.createElement('button');
                        acceptBtn.classList.add('btn', 'btn-success', 'btn-sm');
                        acceptBtn.innerText = "Accept";
                        acceptBtn.addEventListener('click', function () {
                            handleChallengeResponse(user.id, 'accept');
                        });

                        let rejectBtn = document.createElement('button');
                        rejectBtn.classList.add('btn', 'btn-danger', 'btn-sm');
                        rejectBtn.innerText = "Reject";
                        rejectBtn.addEventListener('click', function () {
                            handleChallengeResponse(user.id, 'reject');
                        });

                        li.appendChild(acceptBtn);
                        li.appendChild(rejectBtn);

                    } else if (user.has_challenge === 'sent') {
                        // If a challenge has been sent, show "Pending" badge
                        let pendingBadge = document.createElement('span');
                        pendingBadge.classList.add('badge', 'badge-warning');
                        pendingBadge.innerText = "Pending";
                        li.appendChild(pendingBadge);
                    } else {
                        // Show "Challenge" button if no challenge exists
                        let challengeBtn = document.createElement('button');
                        challengeBtn.classList.add('btn', 'btn-primary', 'btn-sm');
                        challengeBtn.innerText = "Challenge";
                        challengeBtn.addEventListener('click', function () {
                            sendChallenge(user.id);
                        });

                        li.appendChild(challengeBtn);
                    }

                    usersList.appendChild(li);
                });
            })
            .catch(error => console.error('Error fetching available users:', error));
    }

    // Poll every 2 seconds to update the user list and challenges
    setInterval(fetchAvailableUsersAndChallenges, 2000);

    // Define the sendChallenge function
    function sendChallenge(userId) {
        fetch(`/send_challenge/${userId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Update the list
                fetchAvailableUsersAndChallenges();
            } else {
                console.error('Error sending challenge:', data.error);
            }
        })
        .catch(error => console.error('Error:', error));
    }

    // Handle Accept/Reject Challenge
    function handleChallengeResponse(userId, action) {
        fetch(`/handle_challenge/${userId}/${action}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                if (action === 'accept') {
                    // Redirect to the game page using the correct URL pattern
                    window.location.href = `/play/${data.game_id}/`;
                } else {
                    // For rejection, just refresh the list
                    fetchAvailableUsersAndChallenges();  // Update the list immediately
                }
            } else {
                console.error(`Error handling ${action} challenge:`, data.error);
            }
        })
        .catch(error => console.error('Error:', error));
    }
    

    // Attach event listeners to buttons rendered by the template
    function attachEventListeners() {
        document.querySelectorAll('.challenge-btn').forEach(button => {
            button.addEventListener('click', function () {
                const userId = this.getAttribute('data-user-id');
                sendChallenge(userId);
            });
        });

        document.querySelectorAll('.accept-btn').forEach(button => {
            button.addEventListener('click', function () {
                const userId = this.getAttribute('data-user-id');
                handleChallengeResponse(userId, 'accept');
            });
        });

        document.querySelectorAll('.reject-btn').forEach(button => {
            button.addEventListener('click', function () {
                const userId = this.getAttribute('data-user-id');
                handleChallengeResponse(userId, 'reject');
            });
        });
    }

    // Initial attachment of event listeners
    attachEventListeners();
});
