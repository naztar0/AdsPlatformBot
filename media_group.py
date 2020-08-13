from asyncio import sleep


async def media_group(message, state):
    if message.media_group_id:
        data = await state.get_data()
        try:
            data['media_group']['id']
        except KeyError:
            data = {'media_group': {'id': message.media_group_id, 'photo': [], 'video': [], 'caption': ""}}
        except TypeError:
            return
        if message.photo:
            data['media_group']['photo'].append(message.photo[-1].file_id)
        elif message.video:
            data['media_group']['video'].append(message.video.file_id)
        if message.caption:
            data['media_group']['caption'] = message.caption
        media_len = len(data['media_group']['photo']) + len(data['media_group']['video'])
        await state.update_data(data)
        await sleep(0.1)
        data = await state.get_data()
        try:
            if media_len == len(data['media_group']['photo']) + len(data['media_group']['video']):
                return data
        except KeyError:
            return
        except TypeError:
            return
