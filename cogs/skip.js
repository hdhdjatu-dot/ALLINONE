const { useQueue } = require('discord-player');

module.exports = {
    name: 'skip',
    description: 'Current gaana skip karo',
    async execute(message) {
        // Voice channel check
        if (!message.member.voice.channel) {
            return message.reply('Pehle voice channel join karo!');
        }

        // Active queue check karo
        const queue = useQueue(message.guild.id);

        if (!queue || !queue.isPlaying()) {
            return message.reply('Abhi koi gaana nahi chal raha!');
        }

        const currentTrack = queue.currentTrack;
        const success = queue.node.skip();

        return message.channel.send(
            success 
                ? `⏭️ Skipped: **${currentTrack.title}**` 
                : '❌ Skip nahi ho paya!'
        );
    }
};