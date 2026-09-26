# Säkerhet

Rapportera säkerhetsproblem privat genom GitHubs **Private vulnerability reporting** om funktionen är aktiverad för repositoryt. Publicera inte detaljer om en ouppklarad sårbarhet i ett publikt issue.

Appen är avsedd att köras bakom HTTPS och en produktionsserver. Flask-utvecklingsservern ska inte exponeras på internet. API-nycklar används inte, men miljövariabeln `OVERPASS_URL` ska bara kunna ändras av en betrodd administratör.