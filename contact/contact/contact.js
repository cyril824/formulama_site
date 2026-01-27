document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.contact-form');
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const name = document.getElementById('name').value;
        const email = document.getElementById('email').value;
        const message = document.getElementById('message').value;
        
        // Les 4 emails de destination
        const recipients = [
            'matheo.guerin@ensitech.eu',
            'mathys.policarpe@ensitech.eu',
            'edouard.hillion@ensitech.eu',
            'cyril.laurent@ensitech.eu'
        ];
        
        // Créer le corps du mail
        const subject = encodeURIComponent('Contact Formulama - ' + name);
        const body = encodeURIComponent(
            'Nom: ' + name + '\n' +
            'Email: ' + email + '\n\n' +
            'Message:\n' + message
        );
        
        // Ouvrir le client mail avec tous les destinataires
        const mailtoLink = 'mailto:' + recipients.join(',') + '?subject=' + subject + '&body=' + body;
        window.location.href = mailtoLink;
    });
});
