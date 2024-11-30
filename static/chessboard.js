function movePiece() {
    let src = document.getElementById("src").value;
    let dst = document.getElementById("dst").value;

    let srcElement = document.getElementById(src);
    let dstElement = document.getElementById(dst);

    if (srcElement && dstElement) {
        dstElement.innerHTML = srcElement.innerHTML;
        srcElement.innerHTML = '&nbsp;';
    }
}



function resetBoard() {
    window.location.reload();
}






// $(document).ready(function() {
//     // Function to poll for new challenges every 5 seconds
//     function pollChallenges() {
//         $.ajax({
//             url: '/poll_challenges/',  // Polling URL
//             method: 'GET',
//             success: function(response) {
//                 const challenges = response.challenges;

//                 if (challenges.length > 0) {
//                     $('#receivedChallenges').empty();  // Clear any existing challenges
                    
//                     challenges.forEach(function(challenge) {
//                         // Append new challenge data dynamically
//                         $('#receivedChallenges').append(
//                             `<li class="list-group-item">
//                                 New challenge from ${challenge.challenger}
//                                 <button type="submit" name="accept" value="${challenge.challenge_id}" class="btn btn-success btn-sm">Accept</button>
//                                 <button type="submit" name="reject" value="${challenge.challenge_id}" class="btn btn-danger btn-sm">Reject</button>
//                             </li>`
//                         );
//                     });
//                 }
//             },
//             error: function(xhr, status, error) {
//                 console.error('Polling error:', error);
//             }
//         });
//     }

//     // Poll every 5 seconds
//     setInterval(pollChallenges, 5000);
// });

// // Accept and reject challenge functionality (Add this inside the $(document).ready())
// $('body').on('click', 'button[name="accept"]', function() {
//     const challengeId = $(this).val();  // Get challenge ID
//     $.post('/accept_challenge/', { challenge_id: challengeId, csrfmiddlewaretoken: '{{ csrf_token }}' }, function(response) {
//         alert('Challenge accepted!');
//         location.reload();  // Reload the page or update the UI dynamically as needed
//     });
// });

// $('body').on('click', 'button[name="reject"]', function() {
//     const challengeId = $(this).val();  // Get challenge ID
//     $.post('/reject_challenge/', { challenge_id: challengeId, csrfmiddlewaretoken: '{{ csrf_token }}' }, function(response) {
//         alert('Challenge rejected.');
//         location.reload();  // Reload the page or update the UI dynamically as needed
//     });
// });
