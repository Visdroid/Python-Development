const router = require('express').Router();
const ChatController = require('../controllers/ChatController');

router.post('/', ChatController.create);
router.get('/', ChatController.list);
router.delete('/:id', ChatController.remove);

module.exports = router;
