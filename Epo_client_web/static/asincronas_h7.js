/Advertencia boton eliminacion
async function eliminarElemento() {
    if (await confirmarEliminar()) {
        console.log("Elemento eliminado exitosamente.");
        window.location.href = "./backendAdmin/estados";
    } else {
        
        console.log("La operación de eliminación ha sido cancelada.");
    }
}

function confirmarEliminar() {
    return new Promise(resolve => {
        var confirmacion = confirm("¿Estás seguro de que deseas eliminar esto?");
        resolve(confirmacion);
    });
}