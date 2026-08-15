const { useQueue } = require('discord-player');

module.exports = {
    name: 'stop',
    description: 'Music band karo aur queue clear karo',
    async execute(message) {
        if (!message.member.voice.channel) {
            return message.reply('Pehle voice channel join karo!');
        }

        const queue = useQueue(message.guild.id);

        if (!queue) {
            return message.reply('Abhi koi music queue active nahi hai!');
        }

        // Queue clear aur voice channel disconnect
        queue.delete();

        return message.channel.send('⏹️ Music stop kar diya aur queue clear ho gayi!');
    }
};