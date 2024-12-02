// document.addEventListener("DOMContentLoaded", function () {
   

//     // Define the sendChallenge function
//     function sendChallenge(userId) {
//         fetch(`/send_challenge/${userId}/`, {
//             method: 'POST',
//             headers: {
//                 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
//             }
//         })
//         .then(response => response.json())
//         .then(data => {
//             if (data.status === 'success') {
//                 // Update the list
//                 fetchAvailableUsersAndChallenges();
//             } else {
//                 console.error('Error sending challenge:', data.error);
//             }
//         })
//         .catch(error => console.error('Error:', error));
//     }

//     // Handle Accept/Reject Challenge
//     function handleChallengeResponse(userId, action) {
//         fetch(`/handle_challenge/${userId}/${action}/`, {
//             method: 'POST',
//             headers: {
//                 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
//             }
//         })
//         .then(response => response.json())
//         .then(data => {
//             if (data.status === 'success') {
//                 if (action === 'accept') {
//                     // Redirect to the game page using the correct URL pattern
//                     window.location.href = `/play/${data.game_id}/`;
//                 } else {
//                     // For rejection, just refresh the list
//                     fetchAvailableUsersAndChallenges();  // Update the list immediately
//                 }
//             } else {
//                 console.error(`Error handling ${action} challenge:`, data.error);
//             }
//         })
//         .catch(error => console.error('Error:', error));
//     }
    

//     // Attach event listeners to buttons rendered by the template
//     function attachEventListeners() {
//         document.querySelectorAll('.challenge-btn').forEach(button => {
//             button.addEventListener('click', function () {
//                 const userId = this.getAttribute('data-user-id');
//                 sendChallenge(userId);
//             });
//         });

//         document.querySelectorAll('.accept-btn').forEach(button => {
//             button.addEventListener('click', function () {
//                 const userId = this.getAttribute('data-user-id');
//                 handleChallengeResponse(userId, 'accept');
//             });
//         });

//         document.querySelectorAll('.reject-btn').forEach(button => {
//             button.addEventListener('click', function () {
//                 const userId = this.getAttribute('data-user-id');
//                 handleChallengeResponse(userId, 'reject');
//             });
//         });
//     }

//     // Initial attachment of event listeners
//     attachEventListeners();
// });
