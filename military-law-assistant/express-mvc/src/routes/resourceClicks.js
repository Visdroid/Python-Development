const router = require('express').Router();
const ResourceClickController = require('../controllers/ResourceClickController');

router.post('/', ResourceClickController.create);
router.get('/', ResourceClickController.list);

module.exports = router;
