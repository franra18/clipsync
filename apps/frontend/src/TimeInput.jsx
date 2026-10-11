import React from 'react';

export default function TimeInput({ label, value = '00:00', onChange }) {
    // Extrae solo los dígitos (máximo 4)
    const getDigits = (val) => String(val || '').replace(/\D/g, '').slice(0, 4);

    // Formatea los dígitos en HH:MM (MM:SS) desplazando hacia la izquierda
    const formatDigits = (digits) => {
        if (!digits) return '00:00';
        const padded = digits.padStart(4, '0');
        return `${padded.slice(0, 2)}:${padded.slice(2, 4)}`;
    };

    const handleKeyDown = (e) => {
        const currentDigits = getDigits(value);

        // Si es un número (0-9)
        if (/^[0-9]$/.test(e.key)) {
            e.preventDefault();
            // Añade el nuevo dígito al final y conserva máximo los últimos 4
            const newDigits = (currentDigits + e.key).slice(-4);
            onChange(formatDigits(newDigits));
        }

        // Si se pulsa borrar (Backspace)
        if (e.key === 'Backspace') {
            e.preventDefault();
            // Quita el último dígito
            const newDigits = currentDigits.slice(0, -1);
            onChange(formatDigits(newDigits));
        }

        // Permitir navegación previa (Tab, Escape, Enter, etc.)
        if (['Tab', 'Enter', 'Escape', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
            return;
        }
    };

    return (
        <div>
            <label className="block text-xs font-medium text-zinc-300 mb-2">
                {label}
            </label>
            <input
                type="text"
                inputMode="numeric"
                value={value}
                onKeyDown={handleKeyDown}
                onChange={() => { }} // Prevenimos la modificación por evento nativo para delegar a onKeyDown
                placeholder="00:00"
                className="w-full bg-[#0b0c0e] border border-[#262a33] rounded-md px-3.5 py-2 text-sm text-center font-mono text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-400 transition-colors select-none"
            />
        </div>
    );
}
