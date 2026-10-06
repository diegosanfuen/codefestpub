/*!
 * Estaticos desarrollados para el proyecto H7 aduanas
 * AEAT MIDAF
 */
function mouseOver(element){
        document.getElementById(element).style.backgroundColor = 'red';
        }
function submenu_exp(element){

    for (i=0;i<10;i++)
    {
            if(document.getElementById(element*10+i).style.visibility != 'visible')
            {
                    document.getElementById(element*10+i).style.visibility = 'visible';
                    document.getElementById(element*10+i).style.display = 'block';
            }else{
                    document.getElementById(element*10+i).style.visibility = 'hidden';
                    document.getElementById(element*10+i).style.display = 'none';
            }
    }
}
function mouseOut(element){
        document.getElementById(element).style.backgroundColor = 'gray';
}
function cargarInfo()
{
   top.frames['mainFrame'].location='index2.php';
}
function refrescaTMenu()
{
        setTimeout(refrescaMenu(),20000);
}
function refrescaMenu()
{
        top.frames['leftFrame'].location='menuizdo.php';
}
function cargarInfo()
{
   top.frames['mainFrame'].location='index2.php';
}
function refrescaTMenu()
{
        setTimeout(refrescaMenu(),20000);
}  
document.addEventListener("DOMContentLoaded", function() {
// Esta función se ejecutará una vez que el DOM esté completamente cargado
function cargarContenido(url) {
    fetch(url)
        .then(response => response.text())
        .then(data => {
            // Verifica si el elemento .contenido existe antes de modificar su innerHTML
            const contenido = document.querySelector('.contenido');
            if (contenido) {
                contenido.innerHTML = data;
            } else {
                console.error('El elemento .contenido no fue encontrado en el documento.');
            }
        })
        .catch(error => console.error('Error al cargar el contenido:', error));
    }

function validarFormulario() {
    var modelo = document.getElementById("modelo").value;
    var contexto = document.getElementById("contexto").value;
    var input = document.getElementById("input").value;
    var output = document.getElementById("output").value;
    var file = document.getElementById("file").value;
    var regex = /^[a-zA-Z0-9]*$/;

    if (modelo === '' || contexto === '' || input === '' || output === '' || file === '' ) {
        alert("Por favor, completa todos los campos obligatorios.");
        return false;
    }    
    else if (!regex.test(contexto)) {        
        alert("Por favor, no introdizca espacios ni caracteres especiales en el contexto");
        return false;
    }
    return true;
}
    
function validarURL(input) {
    // Expresión regular para validar una URL
    var contexto = document.getElementById("contexto").value;
    var regex = /^[a-zA-Z0-9]*$/;
    if (!regex.test(contexto)) {
        alert("Por favor, completa todos los campos obligatorios.");
        return false;
    }
    return true;
}
    
function validarTexto(input) {
    var texto = input.value;
    var regex = /^[a-zA-Z0-9]*$/;
    if (!regex.test(texto)) {
        alert("Por favor, ingrese solo letras y números.");
        return false;
    }
    return true;
}

