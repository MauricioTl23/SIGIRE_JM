function toggleSubMenu(event, submenuId) {
    event.preventDefault(); 
    
    const submenu = document.getElementById(submenuId);
    const icon = event.currentTarget.querySelector('.chevron-icon');
    
    if (submenu) {
        submenu.classList.toggle('open');
    }
    
    if (icon) {
        icon.classList.toggle('rotate');
    }
}