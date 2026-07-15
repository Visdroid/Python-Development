const router = require('express').Router();
const CaseSearchController = require('../controllers/CaseSearchController');

router.post('/', CaseSearchController.create);
router.get('/', CaseSearchController.list);

module.exports = router;
