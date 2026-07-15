fetch('https://api.github.com/users/Naman6019/repos?sort=updated')
  .then(res => res.json())
  .then(data => {
    data.slice(0, 15).forEach(r => console.log(`${r.name}: ${r.description} (${r.language})`));
  });
